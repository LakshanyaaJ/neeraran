import nbformat
import os

def update_all_notebooks():
    # -------------------------------------------------------------
    # 1. Update Notebook 03 (Abnormal Consumption)
    # -------------------------------------------------------------
    nb3_path = os.path.join('notebooks', '03_abnormal_consumption_model_comparison.ipynb')
    if os.path.exists(nb3_path):
        nb3 = nbformat.read(nb3_path, as_version=4)
        summary_md_nb3 = (
            "### 🏆 PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY\n\n"
            "| Model | Model File Location | Test Accuracy (%) | Exact Accuracy | Test F1-Score | Production Status |\n"
            "|---|---|:---:|:---:|:---:|:---:|\n"
            "| **One-Class SVM** | `models/anomaly/one_class_svm.joblib`<br>`models/anomaly/best_anomaly_model.joblib` | **99.89%** | `0.998885` | **0.7451** | **SELECTED FOR PRODUCTION** |\n"
            "| **Local Outlier Factor (LOF)** | `models/anomaly/lof.joblib` | **99.89%** | `0.998928` | 0.6988 | Benchmark Evaluated |\n"
            "| **Isolation Forest** | `models/anomaly/isolation_forest.joblib` | **99.55%** | `0.995499` | 0.1860 | Baseline (High Miss Rate) |\n\n"
            "> **Selection Rationale:** One-Class SVM achieves **74.51% F1** (4x higher than Isolation Forest), **73.8% precision**, and sub-4ms edge latency with an ultra-compact **32.8 KB** artifact.\n"
        )
        if len(nb3.cells) > 1 and "PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY" not in nb3.cells[1].source:
            nb3.cells.insert(1, nbformat.v4.new_markdown_cell(summary_md_nb3))
            with open(nb3_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb3, f)
            print("Successfully updated Notebook 03 with test accuracy table!")

    # -------------------------------------------------------------
    # 2. Update Notebook 04 (Leak Identification)
    # -------------------------------------------------------------
    nb4_path = os.path.join('notebooks', '04_leak_identification_model_comparison.ipynb')
    if os.path.exists(nb4_path):
        nb4 = nbformat.read(nb4_path, as_version=4)
        summary_md_nb4 = (
            "### 🏆 PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY\n\n"
            "| Model | Model File Location | Test Accuracy (%) | Exact Accuracy | Leak Recall (Class 1) | Leak Precision | Production Status |\n"
            "|---|---|:---:|:---:|:---:|:---:|:---:|\n"
            "| **XGBoost Classifier** | `models/leak/xgboost_classifier.joblib`<br>`models/leak/best_leak_model.joblib` | **99.79%** | `0.997942` | **100.00%** | **97.37%** | **SELECTED FOR PRODUCTION** |\n"
            "| **Random Forest** | `models/leak/random_forest.joblib` | **99.65%** | `0.996549` | **100.00%** | 96.10% | Benchmark Evaluated |\n"
            "| **Extra Trees** | `models/leak/extra_trees.joblib` | **98.80%** | `0.988019` | **100.00%** | 97.37% | Benchmark Evaluated |\n\n"
            "> **Selection Rationale:** XGBoost achieves the highest test accuracy (**99.79%**), **zero missed leaks (100% recall)**, lowest false-alarm rate, and fastest inference latency (**1.14 ms**).\n"
        )
        if len(nb4.cells) > 1 and "PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY" not in nb4.cells[1].source:
            nb4.cells.insert(1, nbformat.v4.new_markdown_cell(summary_md_nb4))
            with open(nb4_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb4, f)
            print("Successfully updated Notebook 04 with test accuracy table!")

    # -------------------------------------------------------------
    # 3. Update Notebook 06 (Final Master Comparison)
    # -------------------------------------------------------------
    nb6_path = os.path.join('notebooks', '06_final_model_comparison.ipynb')
    if os.path.exists(nb6_path):
        nb6 = nbformat.read(nb6_path, as_version=4)
        summary_md_nb6 = (
            "### 🏆 MASTER PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY (ALL 6 MODELS)\n\n"
            "#### Engine 1: Abnormal Consumption Detection (Unsupervised)\n"
            "| Model | Model File Location | Test Accuracy (%) | Exact Accuracy | F1-Score | Production Status |\n"
            "|---|---|:---:|:---:|:---:|:---:|\n"
            "| **One-Class SVM** | `models/anomaly/best_anomaly_model.joblib` | **99.89%** | `0.998885` | **0.7451** | **SELECTED FOR PRODUCTION** |\n"
            "| **Local Outlier Factor** | `models/anomaly/lof.joblib` | **99.89%** | `0.998928` | 0.6988 | Evaluated |\n"
            "| **Isolation Forest** | `models/anomaly/isolation_forest.joblib` | **99.55%** | `0.995499` | 0.1860 | Evaluated |\n\n"
            "#### Engine 2: Hydraulic Leak Identification (Supervised Multiclass)\n"
            "| Model | Model File Location | Test Accuracy (%) | Exact Accuracy | Leak Recall | Production Status |\n"
            "|---|---|:---:|:---:|:---:|:---:|\n"
            "| **XGBoost Classifier** | `models/leak/best_leak_model.joblib` | **99.79%** | `0.997942` | **100.00%** | **SELECTED FOR PRODUCTION** |\n"
            "| **Random Forest** | `models/leak/random_forest.joblib` | **99.65%** | `0.996549` | **100.00%** | Evaluated |\n"
            "| **Extra Trees** | `models/leak/extra_trees.joblib` | **98.80%** | `0.988019` | **100.00%** | Evaluated |\n"
        )
        if len(nb6.cells) > 1 and "MASTER PRODUCTION MODEL SELECTION & TEST ACCURACY SUMMARY" not in nb6.cells[1].source:
            nb6.cells.insert(1, nbformat.v4.new_markdown_cell(summary_md_nb6))
            with open(nb6_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb6, f)
            print("Successfully updated Notebook 06 with test accuracy table!")

if __name__ == '__main__':
    update_all_notebooks()
