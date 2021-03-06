#!/bin/sh
#conda activate pytorch11_py36
#nohup sh train.sh poweroff > _logs/netG-unet_netD-unet_b4_ep200_201117.out &
set -eu
mkdir -p _logs

#DATASET_DIR="dataset/templete_dataset"
DATASET_DIR="dataset/zalando_dataset_n100"

#----------------------
# model
#----------------------
N_EPOCHES=200
BATCH_SIZE=4
IMAGE_HIGHT=256
IMAGE_WIDTH=192

#NET_G_TYPE="pix2pixhd"
NET_G_TYPE="unet"
#NET_D_TYPE="patchgan"
NET_D_TYPE="unet"

EXPER_NAME=debug
#EXPER_NAME=netG-${NET_G_TYPE}_netD-${NET_D_TYPE}_b${BATCH_SIZE}_ep${N_EPOCHES}

rm -rf tensorboard/${EXPER_NAME}
rm -rf tensorboard/${EXPER_NAME}_valid
if [ ${EXPER_NAME} = "debug" ] ; then
    N_DISPLAY_STEP=10
    N_DISPLAY_VALID_STEP=50
else
    N_DISPLAY_STEP=100
    N_DISPLAY_VALID_STEP=500
fi

python train.py \
    --exper_name ${EXPER_NAME} \
    --n_epoches ${N_EPOCHES} \
    --image_height ${IMAGE_HIGHT} --image_width ${IMAGE_WIDTH} --batch_size ${BATCH_SIZE} \
    --net_G_type ${NET_G_TYPE} --net_D_type ${NET_D_TYPE} \
    --n_diaplay_step ${N_DISPLAY_STEP} --n_display_valid_step ${N_DISPLAY_VALID_STEP} \
    --debug

if [ $1 = "poweroff" ] ; then
    sudo poweroff
    sudo shutdown -h now
fi
