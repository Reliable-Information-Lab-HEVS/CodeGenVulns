import multiprocessing as mp
import time
import os
from concurrent.futures import ProcessPoolExecutor

import torch

import engine
from engine import stopping
from engine import loader
from engine.prompt_template import PROMPT_MODES
from engine.code_parser import CodeParser, PythonParser
from helpers import datasets
from helpers import utils


@utils.duplicate_function_for_gpu_dispatch
def target(name: str, foo, bar = 3):
    print(os.environ['CUDA_VISIBLE_DEVICES'])
    print(f'Number of gpus seen by torch: {torch.cuda.device_count()}')
    # model = engine.HFModel(name)
    # print(f'Gpus as seen by torch: {model.get_gpu_devices()}')


@utils.duplicate_function_for_gpu_dispatch
def target2(name: str, foo, bar = 3):
    time.sleep(5)
    print('target2')



LARGE_MODELS = (
    'bloom-560M',
    'bloom-1.7B',
    'gpt-neoX-20B',
    'opt-30B',
    # 'llama2-70B',
)


if __name__ == '__main__':
    num_gpus = torch.cuda.device_count()

    # with ProcessPoolExecutor(max_workers=num_gpus, mp_context=mp.get_context('spawn'),
    #                                     initializer=utils.set_cuda_visible_device_of_subprocess) as pool:
            
    #         _ = list(pool.map(target, LARGE_MODELS, (3,)*len(LARGE_MODELS), chunksize=1))


    model_footprints = []
    # Estimate number of gpus needed for each model
    for model in LARGE_MODELS:
        int8 = model == 'bloom-176B'
        gpu_needed, _ = loader.estimate_model_gpu_footprint(model, quantization_8bits=int8)
        model_footprints.append(gpu_needed)


    args = ([1,2],)
    utils.dispatch_jobs(LARGE_MODELS, model_footprints, num_gpus, target, args)
    