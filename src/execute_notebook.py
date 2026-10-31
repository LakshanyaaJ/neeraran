import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import sys
import os

def run_notebook(nb_path):
    print(f"Executing {nb_path}...")
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
        
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
    ep.preprocess(nb, {'metadata': {'path': os.path.dirname(nb_path) or '.'}})
    
    with open(nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print(f"Successfully executed and updated {nb_path} with outputs!")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_notebook(sys.argv[1])
    else:
        print("Please provide path to notebook.")
