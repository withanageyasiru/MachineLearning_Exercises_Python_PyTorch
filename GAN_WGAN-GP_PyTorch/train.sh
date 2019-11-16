#!/bin/sh
#source activate pytorch11_py36
#sh train.sh
#tensorboard --logdir tensorboard
set -e

EXEP_NAME=WGAN-GP_train
TENSOR_BOARD_DIR=tensorboard

BATCH_SIZE=256
BATCH_SIZE_TEST=256
N_DISPLAY_STEP=`expr ${BATCH_SIZE} \* 5`
N_DISPLAY_TEST_STEP=`expr ${BATCH_SIZE} \* 20`

if [ -d "${TENSOR_BOARD_DIR}/${EXEP_NAME}" ] ; then
    rm -r ${TENSOR_BOARD_DIR}/${EXEP_NAME}
fi

if [ -d "${TENSOR_BOARD_DIR}/${EXEP_NAME}_test" ] ; then
    rm -r ${TENSOR_BOARD_DIR}/${EXEP_NAME}_test
fi

python train.py \
    --device gpu \
    --exper_name ${EXEP_NAME} \
    --dataset_dir dataset \
    --tensorboard_dir ${TENSOR_BOARD_DIR} \
    --dataset mnist --image_size 64 --n_channels 1 \
    --n_test 5 \
    --n_epoches 10 --batch_size ${BATCH_SIZE} --batch_size_test ${BATCH_SIZE_TEST} \
    --lr 0.0001 --beta1 0.999 --beta2 0.5 \
    --n_critic 5 --lambda_wgangp 10.0 \
    --n_display_step ${N_DISPLAY_STEP} --n_display_test_step ${N_DISPLAY_TEST_STEP} \
    --debug
