import copy
import os
import torch
from torch.utils import benchmark

from transformers import AutoTokenizer, AutoModelForCausalLM, StaticCache

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Benchmarking settings
BSZ = [1, 4]
NEW_TOK = [16, 256]
# BSZ = [1]
# NEW_TOK = [16]
N_ITER = 20
MODEL_ID = "google/gemma-2b"
ATTN_IMPL = "sdpa"

# Other constants
FRANCE_ARTICLE = (  # @noqa
    """<s>Marseille, France (CNN)The French prosecutor leading an investigation into the crash of Germanwings Flight 9525 insisted Wednesday that he was not aware of any video footage from on board the plane. Marseille prosecutor Brice Robin told CNN that "so far no videos were used in the crash investigation." He added, "A person who has such a video needs to immediately give it to the investigators." Robin\'s comments follow claims by two magazines, German daily Bild and French Paris Match, of a cell phone video showing the harrowing final seconds from on board Germanwings Flight 9525 as it crashed into the French Alps. All 150 on board were killed. Paris Match and Bild reported that the video was recovered from a phone at the wreckage site. The two publications described the supposed video, but did not post it on their websites. The publications said that they watched the video, which was found by a source close to the investigation. \"One can hear cries of 'My God' in several languages,\" Paris Match reported. "Metallic banging can also be heard more than three times, perhaps of the pilot trying to open the cockpit door with a heavy object.  Towards the end, after a heavy shake, stronger than the others, the screaming intensifies. Then nothing." "It is a very disturbing scene," said Julian Reichelt, editor-in-chief of Bild online. An official with France's accident investigation agency, the BEA, said the agency is not aware of any such video. Lt. Col. Jean-Marc Menichini, a French Gendarmerie spokesman in charge of communications on rescue efforts around the Germanwings crash site, told CNN that the reports were "completely wrong" and "unwarranted." Cell phones have been collected at the site, he said, but that they "hadn\'t been exploited yet." Menichini said he believed the cell phones would need to be sent to the Criminal Research Institute in Rosny sous-Bois, near Paris, in order to be analyzed by specialized technicians working hand-in-hand with investigators. But none of the cell phones found so far have been sent to the institute, Menichini said. Asked whether staff involved in the search could have leaked a memory card to the media, Menichini answered with a categorical "no." Reichelt told "Erin Burnett: Outfront" that he had watched the video and stood by the report, saying Bild and Paris Match are "very confident" that the clip is real. He noted that investigators only revealed they\'d recovered cell phones from the crash site after Bild and Paris Match published their reports. "That is something we did not know before. ... Overall we can say many things of the investigation weren't revealed by the investigation at the beginning," he said. What was mental state of Germanwings co-pilot? German airline Lufthansa confirmed Tuesday that co-pilot Andreas Lubitz had battled depression years before he took the controls of Germanwings Flight 9525, which he's accused of deliberately crashing last week in the French Alps. Lubitz told his Lufthansa flight training school in 2009 that he had a "previous episode of severe depression," the airline said Tuesday. Email correspondence between Lubitz and the school discovered in an internal investigation, Lufthansa said, included medical documents he submitted in connection with resuming his flight training. The announcement indicates that Lufthansa, the parent company of Germanwings, knew of Lubitz's battle with depression, allowed him to continue training and ultimately put him in the cockpit. Lufthansa, whose CEO Carsten Spohr previously said Lubitz was 100% fit to fly, described its statement Tuesday as a "swift and seamless clarification" and said it was sharing the information and documents -- including training and medical records -- with public prosecutors. Spohr traveled to the crash site Wednesday, where recovery teams have been working for the past week to recover human remains and plane debris scattered across a steep mountainside. He saw the crisis center set up in Seyne-les-Alpes, laid a wreath in the village of Le Vernet, closer to the crash site, where grieving families have left flowers at a simple stone memorial. Menichini told CNN late Tuesday that no visible human remains were left at the site but recovery teams would keep searching. French President Francois Hollande, speaking Tuesday, said that it should be possible to identify all the victims using DNA analysis by the end of the week, sooner than authorities had previously suggested. In the meantime, the recovery of the victims' personal belongings will start Wednesday, Menichini said. Among those personal belongings could be more cell phones belonging to the 144 passengers and six crew on board. Check out the latest from our correspondents . The details about Lubitz's correspondence with the flight school during his training were among several developments as investigators continued to delve into what caused the crash and Lubitz's possible motive for downing the jet. A Lufthansa spokesperson told CNN on Tuesday that Lubitz had a valid medical certificate, had passed all his examinations and "held all the licenses required." Earlier, a spokesman for the prosecutor\'s office in Dusseldorf, Christoph Kumpa, said medical records reveal Lubitz suffered from suicidal tendencies at some point before his aviation career and underwent psychotherapy before he got his pilot's license. Kumpa emphasized there's no evidence suggesting Lubitz was suicidal or acting aggressively before the crash. Investigators are looking into whether Lubitz feared his medical condition would cause him to lose his pilot's license, a European government official briefed on the investigation told CNN on Tuesday. While flying was "a big part of his life," the source said, it\'s only one theory being considered. Another source, a law enforcement official briefed on the investigation, also told CNN that authorities believe the primary motive for Lubitz to bring down the plane was that he feared he would not be allowed to fly because of his medical problems. Lubitz's girlfriend told investigators he had seen an eye doctor and a neuropsychologist, both of whom deemed him unfit to work recently and concluded he had psychological issues, the European government official said. But no matter what details emerge about his previous mental health struggles, there's more to the story, said Brian Russell, a forensic psychologist. "Psychology can explain why somebody would turn rage inward on themselves about the fact that maybe they weren't going to keep doing their job and they're upset about that and so they're suicidal," he said. "But there is no mental illness that explains why somebody then feels entitled to also take that rage and turn it outward on 149 other people who had nothing to do with the person's problems." Germanwings crash compensation: What we know . Who was the captain of Germanwings Flight 9525? CNN's Margot Haddad reported from Marseille and Pamela Brown from Dusseldorf, while Laura Smith-Spark wrote from London. CNN's Frederik Pleitgen, Pamela Boykoff, Antonia Mortensen, Sandrine Amiel and Anna-Maja Rappard contributed to this report."""
)


tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.float16, attn_implementation=ATTN_IMPL
).to("cuda")
prompt_length = tokenizer([FRANCE_ARTICLE], return_tensors="pt").input_ids.shape[1]
label_ms_per_token = f"Throughput (time/foward pass, prompt = {prompt_length} tokens)"
label_first_step = f"First call (time, prompt = {prompt_length} tokens)"


def print_results(all_results):
    print("\n")
    compare = benchmark.Compare(all_results)
    compare.trim_significant_figures()
    compare.colorize(rowwise = True)
    compare.print()


def time_generate_call(model, task, ms_per_token, first_step, static_cache=False):
    for bsz in BSZ:
        for max_new_tokens in NEW_TOK:
            input_ids = tokenizer([FRANCE_ARTICLE] * bsz, return_tensors="pt").to("cuda")
            description = f"batch size, max_new_tokens: {bsz, max_new_tokens}"
            task_spec_ms_per_token = benchmark.TaskSpec(
                stmt="", setup="", description=task, label=label_ms_per_token, sub_label=description
            )
            task_spec_ms_first_step = benchmark.TaskSpec(
                stmt="", setup="", description=task, label=label_first_step, sub_label=description
            )

            # generate EXACTLY `max_new_tokens` tokens (no early termination due to `eos_token_id`)
            generation_kwargs = {
                "max_new_tokens": max_new_tokens,
                "min_new_tokens": max_new_tokens,
                "eos_token_id": None,
                "do_sample": False,
            }
            generation_config = copy.deepcopy(model.generation_config)
            generation_config.update(**generation_kwargs)

            past_key_values = None
            if static_cache:
                past_key_values = StaticCache(
                    config=model.config,
                    max_batch_size=bsz,
                    max_cache_len=max_new_tokens + prompt_length,
                    device=model.device,
                    dtype=model.dtype,
                )

            torch.compiler.reset()
            results = []
            for _ in range(N_ITER):
                start = torch.cuda.Event(enable_timing=True)
                end = torch.cuda.Event(enable_timing=True)
                start.record()
                gen_out = model.generate(
                    **input_ids, generation_config=generation_config, past_key_values=past_key_values
                )
                end.record()
                torch.cuda.synchronize()
                total_time = start.elapsed_time(end) / 1000  # time in seconds
                time_per_forward = total_time / max_new_tokens
                assert gen_out.shape[1] == max_new_tokens + prompt_length
                results.append(time_per_forward)
                if static_cache:
                    past_key_values.reset()

            ms_per_token.append(benchmark.Measurement(1, results[3:], task_spec_ms_per_token, metadata=None))
            first_step.append(benchmark.Measurement(
                1, [results[0] * max_new_tokens], task_spec_ms_first_step, metadata=None)
            )
            print_results(ms_per_token)
            print_results(first_step)
            print("*" * 80)


ms_per_token = []
first_step = []

# dynamic
time_generate_call(model, "dynamic", ms_per_token, first_step)

# static
time_generate_call(model, "static", ms_per_token, first_step, static_cache=True)

# static + forward compiled
torch.compiler.reset()
model.forward = torch.compile(model.forward, mode="reduce-overhead", fullgraph=True)
time_generate_call(model, "static + fwd compiled", ms_per_token, first_step, static_cache=True)

# generate compiled
torch.compiler.reset()
model.generate = torch.compile(model.generate, mode="reduce-overhead", fullgraph=True)
time_generate_call(model, "generate compiled", ms_per_token, first_step, static_cache=True)