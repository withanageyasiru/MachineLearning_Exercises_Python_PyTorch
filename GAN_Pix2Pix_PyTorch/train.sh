#!/bin/sh
#source activate pytorch11_py36
#nohup sh train.sh > _logs/train_hinge_1.out &
#nohup tensorboard --logdir tensorboard --port 6006 &
set -eu

N_EPOCHES=100
BATCH_SIZE=32
BATCH_SIZE_TEST=64
N_DISPLAY_STEP=10
N_DISPLAY_TEST_STEP=35
N_SAVE_STEP=10000

#GAN_TYPE=vanilla
#GAN_TYPE=lsgan
GAN_TYPE=hinge

NETWORK_D_TYPE=PatchGAN
#NETWORK_D_TYPE=vanilla

#-------------------
# Pix2Pix
#-------------------
mkdir -p ${PWD}/_logs
EXEP_NAME=Pix2Pix_train_D_gantype_${GAN_TYPE}_${NETWORK_D_TYPE}_Epoch${N_EPOCHES}_200114_1
TENSOR_BOARD_DIR=../tensorboard
if [ -d "${TENSOR_BOARD_DIR}/${EXEP_NAME}" ] ; then
    rm -r ${TENSOR_BOARD_DIR}/${EXEP_NAME}
fi
if [ -d "${TENSOR_BOARD_DIR}/${EXEP_NAME}_test" ] ; then
    rm -r ${TENSOR_BOARD_DIR}/${EXEP_NAME}_test
fi

RESULTS_DIR=results
if [ -d "${RESULTS_DIR}/${EXEP_NAME}" ] ; then
    rm -r ${RESULTS_DIR}/${EXEP_NAME}
fi

python train.py \
    --device gpu \
    --exper_name ${EXEP_NAME} \
    --dataset_dir ../dataset/maps \
    --results_dir ${RESULTS_DIR} \
    --tensorboard_dir ${TENSOR_BOARD_DIR} \
    --save_checkpoints_dir checkpoints --n_save_step ${N_SAVE_STEP} \
    --image_size 64 \
    --n_test 5000 \
    --n_epoches ${N_EPOCHES} --batch_size ${BATCH_SIZE} --batch_size_test ${BATCH_SIZE_TEST} \
    --lr 0.0002 --beta1 0.5 --beta2 0.999 \
    --n_display_step ${N_DISPLAY_STEP} --n_display_test_step ${N_DISPLAY_TEST_STEP} \
    --gan_type ${GAN_TYPE} \
    --unetG_dropout 0.5 --networkD_type ${NETWORK_D_TYPE} \
    --debug > _logs/${EXEP_NAME}.out

#sudo poweroff