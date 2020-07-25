import os
import argparse
import numpy as np
import pandas as pd
import random
from tqdm import tqdm
from PIL import Image
import cv2

# sklearn
from sklearn.model_selection import train_test_split

# PyTorch
import torch
from torch.utils.data import DataLoader, Dataset, Subset
import torch.optim as optim
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torchvision.utils import save_image
from tensorboardX import SummaryWriter

# 自作モジュール
from data.pf_dataset import PFDataset, PFDataLoader
from models.geometric_matching_cnn import GeometricMatchingCNN
from models.geo_transform import AffineTransform, TpsTransform
from utils.utils import save_checkpoint, load_checkpoint
from utils.utils import board_add_image, board_add_images, save_image_w_norm

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--exper_name", default="debug", help="実験名")
    parser.add_argument("--dataset_dir", type=str, default="proposal-flow-willow/PF-dataset")
    parser.add_argument("--results_dir", type=str, default="results")
    parser.add_argument('--load_checkpoints_path', type=str, default="", help="モデルの読み込みファイルのパス")
    parser.add_argument('--tensorboard_dir', type=str, default="tensorboard", help="TensorBoard のディレクトリ")
    parser.add_argument('--geometric_model', choices=['affine','tps','hom'], default="affine", help="幾何学的変換モデル")
    parser.add_argument('--n_samplings', type=int, default=100000, help="サンプリング最大数")
    parser.add_argument('--batch_size_test', type=int, default=1, help="バッチサイズ")
    parser.add_argument('--image_height', type=int, default=240, help="入力画像の高さ（pixel単位）")
    parser.add_argument('--image_width', type=int, default=240, help="入力画像の幅（pixel単位）")
    parser.add_argument("--seed", type=int, default=71)
    parser.add_argument('--device', choices=['cpu', 'gpu'], default="gpu", help="使用デバイス (CPU or GPU)")
    parser.add_argument('--n_workers', type=int, default=4, help="CPUの並列化数（0 で並列化なし）")
    parser.add_argument('--use_cuda_benchmark', action='store_true', help="torch.backends.cudnn.benchmark の使用有効化")
    parser.add_argument('--use_cuda_deterministic', action='store_true', help="再現性確保のために cuDNN に決定論的振る舞い有効化")
    parser.add_argument('--detect_nan', action='store_true')
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()
    if( args.debug ):
        for key, value in vars(args).items():
            print('%s: %s' % (str(key), str(value)))

    # 出力フォルダの作成
    if not os.path.isdir(args.results_dir):
        os.mkdir(args.results_dir)
    if not os.path.isdir( os.path.join(args.results_dir, args.exper_name) ):
        os.mkdir(os.path.join(args.results_dir, args.exper_name))
    if not os.path.isdir( os.path.join(args.results_dir, args.exper_name, "output" ) ):
        os.mkdir(os.path.join(args.results_dir, args.exper_name, "output"))

    # 実行 Device の設定
    if( args.device == "gpu" ):
        use_cuda = torch.cuda.is_available()
        if( use_cuda == True ):
            device = torch.device( "cuda" )
            #torch.cuda.set_device(args.gpu_ids[0])
            print( "実行デバイス :", device)
            print( "GPU名 :", torch.cuda.get_device_name(device))
            print("torch.cuda.current_device() =", torch.cuda.current_device())
        else:
            print( "can't using gpu." )
            device = torch.device( "cpu" )
            print( "実行デバイス :", device)
    else:
        device = torch.device( "cpu" )
        print( "実行デバイス :", device)

    # seed 値の固定
    if( args.use_cuda_deterministic ):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    np.random.seed(args.seed)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    # NAN 値の検出
    if( args.detect_nan ):
        torch.autograd.set_detect_anomaly(True)

    # tensorboard 出力
    board_test = SummaryWriter( log_dir = os.path.join(args.tensorboard_dir, args.exper_name + "_test") )

    #================================
    # データセットの読み込み
    #================================    
    # 学習用データセットとテスト用データセットの設定
    ds_test = PFDataset( args, args.dataset_dir, image_height = args.image_height, image_width = args.image_width, debug = args.debug )
    dloader_test = torch.utils.data.DataLoader(ds_test, batch_size=args.batch_size_test, shuffle = False, num_workers = args.n_workers, pin_memory = True )

    #================================
    # モデルの構造を定義する。
    #================================
    # GeometricMatchingCNN モデル
    if( args.geometric_model == "affine" ):
        model_G = GeometricMatchingCNN( n_out_channels = 6 ).to(device)
    elif( args.geometric_model == "tps" ):
        model_G = GeometricMatchingCNN( n_out_channels = 18 ).to(device)
    elif( args.geometric_model == "hom" ):
        model_G = GeometricMatchingCNN( n_out_channels = 9 ).to(device)
    else:
        NotImplementedError()

    # 幾何学的変換モデル
    if( args.geometric_model == "affine" ):
        geo_transform = AffineTransform( image_height = args.image_height, image_width = args.image_width, n_out_channels = 3, padding_mode = "border" )
    elif( args.geometric_model == "tps" ):
        geo_transform = TpsTransform( device = device, image_height = args.image_height, image_width = args.image_width, use_regular_grid = True, grid_size = 3, reg_factor = 0, padding_mode = "border" )
    else:
        NotImplementedError()

    if( args.debug ):
        print( "model_G :\n", model_G )
        print( "geo_transform :\n", geo_transform )

    # モデルを読み込む
    if not args.load_checkpoints_path == '' and os.path.exists(args.load_checkpoints_path):
        load_checkpoint(model_G, device, args.load_checkpoints_path )
        
    #================================
    # モデルの推論
    #================================    
    print("Starting Testing Loop...")
    n_print = 1
    model_G.eval()
    for step, inputs in enumerate( tqdm( dloader_test, desc = "Samplings" ) ):
        if inputs["image_s"].shape[0] != args.batch_size_test:
            break

        # ミニバッチデータを GPU へ転送
        image_s_name = inputs["image_s_name"]
        image_t_name = inputs["image_t_name"]
        image_s = inputs["image_s"].to(device)
        image_t = inputs["image_t"].to(device)
        if( args.debug and n_print > 0):
            print( "image_s.shape : ", image_s.shape )
            print( "image_t.shape : ", image_t.shape )

        #----------------------------------------------------
        # 生成器の推論処理
        #----------------------------------------------------
        # 変換パラメータを推論
        with torch.no_grad():
            theta = model_G( image_s, image_t )
            if( args.debug and n_print > 0 ):
                print( "theta.shape : ", theta.shape )

            # 幾何学的変換モデルを用いて変換パラメータで変形
            warp_image, grid = geo_transform( image_s, theta )

        #====================================================
        # 推論結果の保存
        #====================================================
        save_image_w_norm( warp_image, os.path.join( args.results_dir, args.exper_name, "output", image_s_name[0].split(".")[0] + "-" + image_t_name[0].split(".")[0] + ".png" ) )

        # tensorboard
        visuals = [
            [ image_s, image_t, warp_image ],
        ]
        board_add_images(board_test, 'test', visuals, step+1)

        n_print -= 1
        if( step >= args.n_samplings ):
            break
