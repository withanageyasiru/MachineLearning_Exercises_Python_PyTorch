# -*- coding:utf-8 -*-
import os
import torch
import torch.nn as nn

def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.normal_(m.weight.data, 1.0, 0.02)
        nn.init.constant_(m.bias.data, 0)

#====================================
# UNet
#====================================
class UNet4Generator( nn.Module ):
    """
    4層の UNet 構造での生成器
    """
    def __init__(
        self,
        n_in_channels = 3,
        n_out_channels = 3,
        n_fmaps = 64,
    ):
        super( UNet4Generator, self ).__init__()

        def conv_block( in_dim, out_dim ):
            model = nn.Sequential(
                nn.Conv2d( in_dim, out_dim, kernel_size=3, stride=1, padding=1 ),
                nn.BatchNorm2d( out_dim ),
                nn.LeakyReLU( 0.2, inplace=True ),

                nn.Conv2d( out_dim, out_dim, kernel_size=3, stride=1, padding=1 ),
                nn.BatchNorm2d( out_dim ),
            )
            return model

        def dconv_block( in_dim, out_dim ):
            model = nn.Sequential(
                nn.ConvTranspose2d( in_dim, out_dim, kernel_size=3, stride=2, padding=1,output_padding=1 ),
                nn.BatchNorm2d(out_dim),
                nn.LeakyReLU( 0.2, inplace=True ),
            )
            return model

        # Encoder（ダウンサンプリング）
        self.conv1 = conv_block( n_in_channels, n_fmaps )
        self.pool1 = nn.MaxPool2d( kernel_size=2, stride=2, padding=0 )
        self.conv2 = conv_block( n_fmaps*1, n_fmaps*2 )
        self.pool2 = nn.MaxPool2d( kernel_size=2, stride=2, padding=0 )
        self.conv3 = conv_block( n_fmaps*2, n_fmaps*4 )
        self.pool3 = nn.MaxPool2d( kernel_size=2, stride=2, padding=0 )
        self.conv4 = conv_block( n_fmaps*4, n_fmaps*8 )
        self.pool4 = nn.MaxPool2d( kernel_size=2, stride=2, padding=0 )

        #
        self.bridge=conv_block( n_fmaps*8, n_fmaps*16 )

        # Decoder（アップサンプリング）
        self.dconv1 = dconv_block( n_fmaps*16, n_fmaps*8 )
        self.up1 = conv_block( n_fmaps*16, n_fmaps*8 )
        self.dconv2 = dconv_block( n_fmaps*8, n_fmaps*4 )
        self.up2 = conv_block( n_fmaps*8, n_fmaps*4 )
        self.dconv3 = dconv_block( n_fmaps*4, n_fmaps*2 )
        self.up3 = conv_block( n_fmaps*4, n_fmaps*2 )
        self.dconv4 = dconv_block( n_fmaps*2, n_fmaps*1 )
        self.up4 = conv_block( n_fmaps*2, n_fmaps*1 )

        # 出力層
        self.out_layer = nn.Sequential(
		    nn.Conv2d( n_fmaps, n_out_channels, 3, 1, 1 ),
		    nn.Tanh(),
		)
        return

    def forward( self, input ):
        # Encoder（ダウンサンプリング）
        conv1 = self.conv1( input )
        pool1 = self.pool1( conv1 )
        conv2 = self.conv2( pool1 )
        pool2 = self.pool2( conv2 )
        conv3 = self.conv3( pool2 )
        pool3 = self.pool3( conv3 )
        conv4 = self.conv4( pool3 )
        pool4 = self.pool4( conv4 )

        #
        bridge = self.bridge( pool4 )

        # Decoder（アップサンプリング）& skip connection
        dconv1 = self.dconv1(bridge)

        concat1 = torch.cat( [dconv1,conv4], dim=1 )
        up1 = self.up1(concat1)

        dconv2 = self.dconv2(up1)
        concat2 = torch.cat( [dconv2,conv3], dim=1 )

        up2 = self.up2(concat2)
        dconv3 = self.dconv3(up2)
        concat3 = torch.cat( [dconv3,conv2], dim=1 )

        up3 = self.up3(concat3)
        dconv4 = self.dconv4(up3)
        concat4 = torch.cat( [dconv4,conv1], dim=1 )

        up4 = self.up4(concat4)

        # 出力層
        output = self.out_layer( up4 )

        return output


class UNetGenerator(nn.Module):
    """
    任意の upsampling / downsampling 層数での UNet 生成器
    """
    def __init__(self, n_in_channels=3, n_out_channels=3, n_fmaps=64, n_downsampling=4, norm_type='batch'):
        super( UNetGenerator, self ).__init__()
        self.n_downsampling = n_downsampling
        if norm_type == 'batch':
            self.norm_layer = functools.partial(nn.BatchNorm2d, affine=True)
        elif norm_type == 'instance':
            self.norm_layer = functools.partial(nn.InstanceNorm2d, affine=False)
        else:
            raise NotImplementedError()

        def conv_block( in_dim, out_dim ):
            model = nn.Sequential(
                nn.Conv2d( in_dim, out_dim, kernel_size=3, stride=1, padding=1 ),
                self.norm_layer( out_dim ),
                nn.LeakyReLU( 0.2, inplace=True ),
                nn.Conv2d( out_dim, out_dim, kernel_size=3, stride=1, padding=1 ),
                self.norm_layer( out_dim ),
            )
            return model

        def dconv_block( in_dim, out_dim ):
            model = nn.Sequential(
                nn.ConvTranspose2d( in_dim, out_dim, kernel_size=3, stride=2, padding=1,output_padding=1 ),
                self.norm_layer(out_dim),
                nn.LeakyReLU( 0.2, inplace=True ),
            )
            return model
        
        # encoder
        in_dim = n_in_channels
        out_dim = n_fmaps
        self.encoder = nn.ModuleDict()
        for i in range(n_downsampling):
            self.encoder["conv_{}".format(i+1)] = conv_block( in_dim, out_dim )
            self.encoder["pool_{}".format(i+1)] = nn.MaxPool2d( kernel_size=2, stride=2, padding=0 )
            in_dim = n_fmaps * (2**(i))
            out_dim = n_fmaps * (2**(i+1))

        # bottle neck
        self.bridge = conv_block( n_fmaps * (2**(n_downsampling-1)), n_fmaps*(2**(n_downsampling-1))*2 )

        # decoder
        self.decoder = nn.ModuleDict()
        for i in range(n_downsampling):
            in_dim = n_fmaps * (2**(n_downsampling-i))
            out_dim = int( in_dim / 2 )
            self.decoder["deconv_{}".format(i+1)] = dconv_block( in_dim, out_dim )
            self.decoder["conv_{}".format(i+1)] = conv_block( in_dim, out_dim )

        # 出力層
        self.out_layer = nn.Sequential( nn.Conv2d( n_fmaps, n_out_channels, 3, 1, 1 ), nn.Tanh() )
        return

    def forward(self, input):
        output = input

        skip_connections = []
        for i in range(self.n_downsampling):
            output = self.encoder["conv_{}".format(i+1)](output)
            skip_connections.append( output.clone() )
            output = self.encoder["pool_{}".format(i+1)](output)
            #print("[UNetGenerator] encoder_{} / output.shape={}".format(i+1, output.shape) )

        output = self.bridge(output)
        #print("[UNetGenerator] bridge / output.shape={}".format(i+1, output.shape) )

        for i in range(self.n_downsampling):
            output = self.decoder["deconv_{}".format(i+1)](output)
            output = self.decoder["conv_{}".format(i+1)]( torch.cat( [output, skip_connections[-1 - i]], dim=1 ) )
            #print("[UNetGenerator] decoder_{} / output.shape={}".format(i+1, output.shape) )

        output = self.out_layer(output)
        #print("[UNetGenerator] out_layer / output.shape : ", output.shape )
        return output