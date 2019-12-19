#!/bin/sh
{
python train.py /checkpoint/omerlevy/mandar_data/bookwiki_aml_cased --total-num-update 300000 --max-update 300000  --save-interval 1 --arch cased_bert_hf --task  span_bert --optimizer adam --lr-scheduler polynomial_decay --lr 0.0005  --min-lr 1e-09  --criterion no_nsp_bert_loss  --max-tokens 4096 --tokens-per-sample 512 --weight-decay 0.01  --skip-invalid-size-inputs-valid-test --log-format json --log-interval 2000 --save-interval-updates 50000 --keep-interval-updates 50000 --update-freq 1 --seed 1 --save-dir fast_models/base_no_nsp_random --fp16 --warmup-updates 10000 --schemes [\"random\"] --distributed-port 12580 --distributed-world-size 256 --validate-interval 1  --clip-norm 1.0 --adam-eps 1e-8 --short-seq-prob 0.0 --return-only-spans --clamp-attention --no-nsp
kill -9 $$
} & 
child_pid=$!
trap "echo 'TERM Signal received';" TERM
trap "echo 'Signal received'; if [ "$SLURM_PROCID" -eq "0" ]; then sbatch fast_slurm/base_no_nsp_random.slrm; fi; kill -9 $child_pid; " USR1
while true; do     sleep 1; done
