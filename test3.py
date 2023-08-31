from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import torch
from accelerate import init_empty_weights, load_checkpoint_and_dispatch, infer_auto_device_map
import time

model_name = 'facebook/opt-13b'

max_memory = {0: '3GiB', 1: '25GiB', 2:'25GiB'}
device_map = 'balanced'
# t0 = time.time()
# model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map=device_map,
#                                              max_memory=max_memory)
# dt0 = time.time() - t0
# print(f'Total time to load: {dt0:.2f} s')

# for i in range(torch.cuda.device_count()):
#     print(f'GPU {i}: {torch.cuda.memory_allocated(i) / 1024**3:.2f} GiB')

# print(model.hf_device_map)


t0 = time.time()
config = AutoConfig.from_pretrained(model_name, torch_dtype=torch.float16)
with init_empty_weights():
    model = AutoModelForCausalLM.from_config(config)
    model.tie_weights()
    device_map = infer_auto_device_map(model, max_memory=max_memory, torch_dtype=torch.float16)
dt0 = time.time() - t0
print(f'Time to compute device_map: {dt0:.2f} s')

t1 = time.time()
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map=device_map)
dt1 = time.time() - t1
print(f'Time to load model: {dt1:.2f} s')

print(f'Total time: {dt0 + dt1:.2f} s')

for i in range(torch.cuda.device_count()):
    print(f'GPU {i}: {torch.cuda.memory_allocated(i) / 1024**3:.2f} GiB')

print(model.hf_device_map)