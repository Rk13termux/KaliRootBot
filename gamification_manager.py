import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

ASSETS_DIR = "assets"

def ensure_assets_dir():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)

def generate_user_stats_chart(user_id: int, stats: dict) -> str:
    """
    Generates a stats chart for the user.
    stats dict should contain: 'modules_completed', 'ai_usage', 'xp', 'level'
    """
    try:
        ensure_assets_dir()
        
        # Data
        categories = ['Módulos', 'Consultas IA', 'Nivel', 'XP (x100)']
        values = [
            stats.get('modules_completed', 0),
            stats.get('ai_usage', 0),
            stats.get('level', 1),
            stats.get('xp', 0) / 100
        ]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 4))
        
        # Bar chart
        bars = ax.bar(categories, values, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
        
        # Add values on top
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, round(yval, 1), ha='center', va='bottom', fontweight='bold')
            
        ax.set_title('Estadísticas de Hacker', fontsize=14, fontweight='bold')
        ax.set_ylabel('Progreso')
        
        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save
        filename = f"stats_{user_id}_{int(datetime.now().timestamp())}.png"
        path = os.path.join(ASSETS_DIR, filename)
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        
        return path
    except Exception as e:
        logger.exception(f"Error generating stats chart: {e}")
        return None
