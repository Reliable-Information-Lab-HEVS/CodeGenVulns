import os
from tqdm import tqdm

from code_execution import evaluation
from helpers import utils
from helpers import process


files = process.extract_all_human_eval_filenames(category='completions', sort_on_results=True)


if __name__ == '__main__':
    result_files = []
    for file in tqdm(files):
        out_file = evaluation.evaluate_functional_correctness(file, n_workers=6, timeout=3)
        result_files.append(out_file)

    # Extract the results folders we should copy
    result_folders = set([process.parse_human_eval_filename(file)['associated_results_folder'] for file in result_files])
    # Extract the relative paths (relative to current dir, i.e. utils.ROOT_FOLDER)
    result_folders = [os.path.relpath(path) for path in result_folders]
    # This is used to determine which files we need to copy back to the host outside of the docker instance
    utils.save_txt(result_folders, 'folders_to_copy.txt')
