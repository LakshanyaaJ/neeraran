"""
AquaGuard AI - Explainability and Feature Importance Suite
Provides permutation importance, SHAP analysis (for XGBoost), tree feature importances,
and prediction attribution grounded in real sensor measurements.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.inspection import permutation_importance
import shap
import os
from typing import Dict, Any, List

def compute_permutation_importance(model, X_val, y_val, feature_names, scoring='f1_macro', n_repeats=5, random_state=42):
    """Compute permutation feature importance on validation set."""
    perm = permutation_importance(
        model, X_val, y_val,
        scoring=scoring,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=-1
    )
    df_imp = pd.DataFrame({
        'feature': feature_names,
        'importance_mean': perm.importances_mean,
        'importance_std': perm.importances_std
    }).sort_values('importance_mean', ascending=False).reset_index(drop=True)
    return df_imp


def plot_feature_importance(df_imp, title, save_path, top_n=10):
    """Plot horizontal bar chart of top features."""
    plt.figure(figsize=(10, 6))
    top = df_imp.head(top_n)
    sns.barplot(
        x='importance_mean', y='feature', data=top,
        palette='viridis', orient='h'
    )
    plt.title(title, fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Mean Importance (Decrease in Metric)", fontsize=11)
    plt.ylabel("Feature", fontsize=11)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def compute_shap_explanations(xgb_model, X_sample, feature_names, save_summary_path=None):
    """Compute TreeExplainer SHAP values for XGBoost."""
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(X_sample)
    
    if save_summary_path:
        plt.figure(figsize=(10, 6))
        # Handle multiclass or binary shap values
        shap.summary_plot(shap_values, X_sample, feature_names=feature_names, show=False)
        plt.title("SHAP Summary Plot - XGBoost Classifier", fontsize=14, fontweight='bold', pad=15)
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_summary_path), exist_ok=True)
        plt.savefig(save_summary_path, dpi=300, bbox_inches='tight')
        plt.close()
        
    return explainer, shap_values
