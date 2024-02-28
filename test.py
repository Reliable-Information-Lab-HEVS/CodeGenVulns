
import time
import numpy as np

from TextWiz import textwiz
from TextWiz.memory_estimator import LARGE_TEXT

model = textwiz.HFModel('zephyr-7B-beta')

large_tokens = model.tokenizer.encode(LARGE_TEXT)
sizes = [10, 100, 1000, 2000, 4000]
N = 10

res = {}

for input_size in sizes:
    prompt = model.tokenizer.decode(large_tokens[:input_size], skip_special_tokens=True)
    gen_times = []

    for i in range(N):
        t0 = time.time()
        foo = model(prompt, num_return_sequences=1, batch_size=1, max_new_tokens=2)
        gen_times.append(time.time() - t0)

    res[input_size] = np.mean(gen_times)

print(res)