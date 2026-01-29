import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import json
import pickle

# ML imports
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.manifold import TSNE

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Database imports
from app.db import get_session, safe_db_context
from app.models import Score, Response, User

logger = logging.getLogger(__name__)


# ==============================================================================
# EMOTIONAL PROFILE DEFINITIONS
# ==============================================================================

EMOTIONAL_PROFILES = {
    0: {
        "name": "Emotionally Resilient",
        "description": "High emotional intelligence with strong self-regulation and social awareness",
        "characteristics": [
            "Excellent emotional recognition",
            "Strong coping mechanisms",
            "High empathy and social skills",
            "Positive outlook on challenges"
        ],
        "recommendations": [
            "Continue practicing emotional awareness",
            "Consider mentoring others in emotional skills",
            "Explore advanced emotional development techniques"
        ],
        "color": "#4CAF50",  # Green
        "emoji": "🌟"
    },
    1: {
        "name": "Balanced Navigator",
        "description": "Moderate emotional awareness with room for growth in specific areas",
        "characteristics": [
            "Good basic emotional recognition",
            "Developing emotional regulation",
            "Average social awareness",
            "Occasional emotional challenges"
        ],
        "recommendations": [
            "Practice daily emotional check-ins",
            "Work on identifying emotional triggers",
            "Develop active listening skills",
            "Try mindfulness exercises"
        ],
        "color": "#2196F3",  # Blue
        "emoji": "⚖️"
    },
    2: {
        "name": "Growth Seeker",
        "description": "Developing emotional intelligence with focus on building core skills",
        "characteristics": [
            "Building emotional vocabulary",
            "Learning to manage stress",
            "Developing empathy skills",
            "Working through emotional patterns"
        ],
        "recommendations": [
            "Start a daily journaling practice",
            "Learn emotional labeling techniques",
            "Practice deep breathing exercises",
            "Seek supportive relationships"
        ],
        "color": "#FF9800",  # Orange
        "emoji": "🌱"
    },
    3: {
        "name": "Emotion Explorer",
        "description": "Beginning the emotional intelligence journey with significant growth potential",
        "characteristics": [
            "Developing emotional awareness",
            "Learning to recognize feelings",
            "Building foundational skills",
            "Open to emotional growth"
        ],
        "recommendations": [
            "Consider professional emotional support",
            "Start with basic emotion identification",
            "Create a supportive environment",
            "Set small, achievable emotional goals"
        ],
        "color": "#9C27B0",  # Purple
        "emoji": "🔍"
    }
}


# ==============================================================================
# FEATURE EXTRACTION
# ==============================================================================

class EmotionalFeatureExtractor:
    """Extract features for clustering from user emotional data.
    
    This class is responsible for extracting numerical features from user scores
    and responses that can be used for clustering emotional profiles.
    """

    def __init__(self):
        """Initialize the feature extractor with predefined feature names."""
        self.feature_names = [
            'avg_total_score',
            'score_std',
            'avg_sentiment',
            'sentiment_std',
            'score_trend',
            'response_consistency',
            'emotional_range',
            'assessment_frequency',
            'avg_response_value',
            'response_variance'
        ]
    
    def extract_user_features(self, username: str) -> Optional[Dict[str, float]]:
        """Extract emotional features for a single user from the database.

        Args:
            username (str): The username to extract features for.

        Returns:
            Optional[Dict[str, float]]: Dictionary containing feature values for the user,
                or None if insufficient data or extraction fails.
        """
        try:
            with safe_db_context() as session:
                # Get all scores for the user
                scores = session.query(Score).filter_by(username=username).order_by(Score.timestamp).all()
                
                if not scores or len(scores) < 1:
                    return None
                
                # Get all responses for the user
                responses = session.query(Response).filter_by(username=username).all()
                
                # Extract score-based features
                score_values = [s.total_score for s in scores if s.total_score is not None]
                sentiment_values = [s.sentiment_score for s in scores if s.sentiment_score is not None]
                
                if not score_values:
                    return None
                
                features = {
                    'username': username,
                    'avg_total_score': np.mean(score_values),
                    'score_std': np.std(score_values) if len(score_values) > 1 else 0,
                    'avg_sentiment': np.mean(sentiment_values) if sentiment_values else 0,
                    'sentiment_std': np.std(sentiment_values) if len(sentiment_values) > 1 else 0,
                    'score_trend': self._calculate_trend(score_values),
                    'response_consistency': self._calculate_consistency(responses),
                    'emotional_range': max(score_values) - min(score_values) if len(score_values) > 1 else 0,
                    'assessment_frequency': len(scores),
                    'avg_response_value': self._avg_response_value(responses),
                    'response_variance': self._response_variance(responses)
                }
                
                return features
                
        except Exception as e:
            logger.error(f"Error extracting features for {username}: {e}")
            return None
    
    def extract_all_users_features(self) -> pd.DataFrame:
        """Extract features for all users in the database.

        Returns:
            pd.DataFrame: DataFrame containing features for all users with sufficient data.
        """
        features_list = []
        
        try:
            with safe_db_context() as session:
                # Get all unique usernames
                usernames = session.query(Score.username).distinct().all()
                usernames = [u[0] for u in usernames if u[0]]
                
        except Exception as e:
            logger.error(f"Error getting usernames: {e}")
            return pd.DataFrame()
        
        for username in usernames:
            features = self.extract_user_features(username)
            if features:
                features_list.append(features)
        
        if not features_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(features_list)
        logger.info(f"Extracted features for {len(df)} users")
        return df
    
    def _calculate_trend(self, scores: List[float]) -> float:
        """Calculate score trend using linear correlation.

        Args:
            scores (List[float]): List of score values over time.

        Returns:
            float: Correlation coefficient indicating trend direction.
                  Positive values indicate improving scores, negative declining.
        """
        if len(scores) < 2:
            return 0.0
        
        # Simple linear trend
        x = np.arange(len(scores))
        if np.std(x) == 0 or np.std(scores) == 0:
            return 0.0
        
        correlation = np.corrcoef(x, scores)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _calculate_consistency(self, responses: List[Response]) -> float:
        """Calculate response consistency across questions.

        Args:
            responses (List[Response]): List of user responses.

        Returns:
            float: Consistency score between 0 and 1, where 1 is most consistent.
        """
        if not responses:
            return 0.0
        
        response_values = [r.response_value for r in responses if r.response_value is not None]
        if len(response_values) < 2:
            return 1.0  # Single response is consistent
        
        # Lower variance = higher consistency
        variance = np.var(response_values)
        max_variance = 4.0  # Max variance for 1-5 scale
        consistency = 1 - (variance / max_variance)
        return max(0, min(1, consistency))
    
    def _avg_response_value(self, responses: List[Response]) -> float:
        """Calculate average response value.

        Args:
            responses (List[Response]): List of user responses.

        Returns:
            float: Average response value, or 2.5 if no responses.
        """
        if not responses:
            return 2.5  # Neutral default
        
        values = [r.response_value for r in responses if r.response_value is not None]
        return np.mean(values) if values else 2.5
    
    def _response_variance(self, responses: List[Response]) -> float:
        """Calculate response variance.

        Args:
            responses (List[Response]): List of user responses.

        Returns:
            float: Variance of response values, or 0.0 if insufficient data.
        """
        if not responses:
            return 0.0
        
        values = [r.response_value for r in responses if r.response_value is not None]
        return np.var(values) if len(values) > 1 else 0.0


# ==============================================================================
# CLUSTERING ENGINE
# ==============================================================================

class EmotionalProfileClusterer:
    """Main clustering engine for emotional profile categorization."""
    
    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        """Initialize the clusterer.

        Args:
            n_clusters (int, optional): Number of emotional profile clusters. Defaults to 4.
            random_state (int, optional): Random seed for reproducibility. Defaults to 42.
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.kmeans = None
        self.hierarchical = None
        self.dbscan = None
        
        self.feature_extractor = EmotionalFeatureExtractor()
        self.is_fitted = False
        self.cluster_centers_ = None
        self.labels_ = None
        self.user_profiles = {}
        
        # Model save path
        self.model_path = Path(__file__).parent / "models" / "clustering"
        self.model_path.mkdir(parents=True, exist_ok=True)
    
    def fit(self, data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Fit the clustering model on user emotional data.
        
        Args:
            data: Optional DataFrame with user features. If None, extracts from database.
            
        Returns:
            Dictionary containing clustering results and metrics
        """
        # Extract features if not provided
        if data is None:
            data = self.feature_extractor.extract_all_users_features()
        
        if data.empty or len(data) < self.n_clusters:
            logger.warning(f"Insufficient data for clustering. Need at least {self.n_clusters} users.")
            return {"error": "Insufficient data for clustering"}
        
        # Prepare feature matrix
        usernames = data['username'].tolist()
        feature_cols = [col for col in data.columns if col != 'username']
        X = data[feature_cols].values
        
        # Handle missing values
        X = np.nan_to_num(X, nan=0.0)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Determine optimal number of clusters if we have enough data
        if len(X_scaled) >= 10:
            optimal_k = self._find_optimal_clusters(X_scaled)
            if optimal_k != self.n_clusters:
                logger.info(f"Optimal clusters: {optimal_k}, using configured: {self.n_clusters}")
        
        # Fit K-Means (primary method)
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
            max_iter=300
        )
        self.labels_ = self.kmeans.fit_predict(X_scaled)
        self.cluster_centers_ = self.kmeans.cluster_centers_
        
        # Fit Hierarchical Clustering (secondary)
        if len(X_scaled) >= self.n_clusters:
            self.hierarchical = AgglomerativeClustering(
                n_clusters=self.n_clusters,
                linkage='ward'
            )
            hierarchical_labels = self.hierarchical.fit_predict(X_scaled)
        else:
            hierarchical_labels = self.labels_
        
        # Fit DBSCAN for anomaly detection
        self.dbscan = DBSCAN(eps=0.5, min_samples=2)
        dbscan_labels = self.dbscan.fit_predict(X_scaled)
        
        # Calculate metrics
        metrics = self._calculate_clustering_metrics(X_scaled, self.labels_)
        
        # Store user profiles
        for username, label in zip(usernames, self.labels_):
            profile_data = EMOTIONAL_PROFILES.get(label, EMOTIONAL_PROFILES[0])
            self.user_profiles[username] = {
                'cluster_id': int(label),
                'profile': profile_data,
                'profile_name': profile_data['name'],
                'assigned_at': datetime.utcnow().isoformat()
            }
        
        # PCA for visualization
        if len(X_scaled) >= 2:
            X_pca = self.pca.fit_transform(X_scaled)
        else:
            X_pca = X_scaled
        
        self.is_fitted = True
        
        # Save model
        self._save_model()
        
        results = {
            'n_users': len(usernames),
            'n_clusters': self.n_clusters,
            'labels': self.labels_.tolist(),
            'usernames': usernames,
            'metrics': metrics,
            'cluster_distribution': self._get_cluster_distribution(),
            'cluster_profiles': self._get_cluster_profiles(X, feature_cols),
            'pca_coordinates': X_pca.tolist() if isinstance(X_pca, np.ndarray) else X_pca
        }
        
        logger.info(f"Clustering complete: {len(usernames)} users into {self.n_clusters} profiles")
        return results
    
    def predict(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Predict emotional profile for a user.
        
        Args:
            username: Username to predict profile for
            
        Returns:
            Dictionary with profile prediction and confidence
        """
        if not self.is_fitted:
            # Try to load existing model
            if not self._load_model():
                logger.warning("Model not fitted. Call fit() first.")
                return None
        
        # Check if user already has a cached profile (from fit)
        if username in self.user_profiles:
            cached = self.user_profiles[username]
            # Ensure it has all needed fields
            if 'profile_name' in cached:
                return cached
            # Convert old format to new format
            cluster_id = cached.get('cluster_id', 0)
            profile = EMOTIONAL_PROFILES.get(cluster_id, EMOTIONAL_PROFILES[0])
            return {
                'username': username,
                'cluster_id': int(cluster_id),
                'profile_name': profile['name'],
                'profile': profile,
                'confidence': 1.0,  # Already assigned during fit
                'features': {},
                'predicted_at': cached.get('assigned_at', datetime.utcnow().isoformat())
            }
        
        # Extract features for the user from database
        features = self.feature_extractor.extract_user_features(username)
        if not features:
            return None
        
        # Prepare feature vector
        feature_cols = self.feature_extractor.feature_names
        X = np.array([[features.get(col, 0) for col in feature_cols]])
        X = np.nan_to_num(X, nan=0.0)
        
        # Scale and predict
        X_scaled = self.scaler.transform(X)
        cluster_id = self.kmeans.predict(X_scaled)[0]
        
        # Calculate confidence based on distance to cluster center
        distances = np.linalg.norm(X_scaled - self.cluster_centers_, axis=1)
        confidence = 1 - (distances[cluster_id] / np.sum(distances))
        
        profile = EMOTIONAL_PROFILES.get(cluster_id, EMOTIONAL_PROFILES[0])
        
        result = {
            'username': username,
            'cluster_id': int(cluster_id),
            'profile_name': profile['name'],
            'profile': profile,
            'confidence': float(confidence),
            'features': features,
            'predicted_at': datetime.utcnow().isoformat()
        }
        
        # Update stored profile
        self.user_profiles[username] = result
        
        return result
    
    def predict_from_features(self, features: Dict[str, float], username: str = "anonymous") -> Optional[Dict[str, Any]]:
        """
        Predict emotional profile from raw features.
        
        Args:
            features: Dictionary of feature values
            username: Optional username for the prediction
            
        Returns:
            Dictionary with profile prediction and confidence
        """
        if not self.is_fitted:
            if not self._load_model():
                logger.warning("Model not fitted. Call fit() first.")
                return None
        
        # Prepare feature vector
        feature_cols = self.feature_extractor.feature_names
        X = np.array([[features.get(col, 0) for col in feature_cols]])
        X = np.nan_to_num(X, nan=0.0)
        
        # Scale and predict
        X_scaled = self.scaler.transform(X)
        cluster_id = self.kmeans.predict(X_scaled)[0]
        
        # Calculate confidence based on distance to cluster center
        distances = np.linalg.norm(X_scaled - self.cluster_centers_, axis=1)
        confidence = 1 - (distances[cluster_id] / np.sum(distances))
        
        profile = EMOTIONAL_PROFILES.get(cluster_id, EMOTIONAL_PROFILES[0])
        
        result = {
            'username': username,
            'cluster_id': int(cluster_id),
            'profile_name': profile['name'],
            'profile': profile,
            'confidence': float(confidence),
            'features': features,
            'predicted_at': datetime.utcnow().isoformat()
        }
        
        return result
    
    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Get the cached emotional profile for a user.

        Args:
            username (str): Username to get profile for.

        Returns:
            Optional[Dict[str, Any]]: User's emotional profile data, or None if not available.
        """
        if username in self.user_profiles:
            return self.user_profiles[username]
        return self.predict(username)
    
    def get_cluster_users(self, cluster_id: int) -> List[str]:
        """Get all users in a specific cluster.

        Args:
            cluster_id (int): The cluster ID to get users for.

        Returns:
            List[str]: List of usernames in the specified cluster.
        """
        return [
            username for username, profile in self.user_profiles.items()
            if profile.get('cluster_id') == cluster_id
        ]
    
    def _find_optimal_clusters(self, X: np.ndarray, max_k: int = 8) -> int:
        """Find optimal number of clusters using silhouette score.

        Args:
            X (np.ndarray): Feature matrix.
            max_k (int, optional): Maximum number of clusters to test. Defaults to 8.

        Returns:
            int: Optimal number of clusters based on silhouette score.
        """
        max_k = min(max_k, len(X) - 1)
        if max_k < 2:
            return 2
        
        silhouette_scores = []
        k_range = range(2, max_k + 1)
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(X)
            try:
                score = silhouette_score(X, labels)
            except ValueError:
                score = -1.0 # Invalid for single cluster
            silhouette_scores.append(score)
        
        optimal_k = k_range[np.argmax(silhouette_scores)]
        return optimal_k
    
    def _calculate_clustering_metrics(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """Calculate clustering quality metrics.

        Args:
            X (np.ndarray): Feature matrix.
            labels (np.ndarray): Cluster labels.

        Returns:
            Dict[str, float]: Dictionary of clustering metrics.
        """
        metrics = {}
        
        # Only calculate if we have valid clusters
        unique_labels = np.unique(labels)
        if len(unique_labels) < 2:
            return {'silhouette_score': 0, 'calinski_harabasz': 0, 'davies_bouldin': float('inf')}
        
        try:
            metrics['silhouette_score'] = float(silhouette_score(X, labels))
        except:
            metrics['silhouette_score'] = 0
        
        try:
            metrics['calinski_harabasz'] = float(calinski_harabasz_score(X, labels))
        except:
            metrics['calinski_harabasz'] = 0
        
        try:
            metrics['davies_bouldin'] = float(davies_bouldin_score(X, labels))
        except:
            metrics['davies_bouldin'] = float('inf')
        
        metrics['inertia'] = float(self.kmeans.inertia_)
        
        return metrics
    
    def _get_cluster_distribution(self) -> Dict[int, int]:
        """Get the distribution of users across clusters.

        Returns:
            Dict[int, int]: Dictionary mapping cluster IDs to user counts.
        """
        if self.labels_ is None:
            return {}
        
        unique, counts = np.unique(self.labels_, return_counts=True)
        return {int(k): int(v) for k, v in zip(unique, counts)}
    
    def _get_cluster_profiles(self, X: np.ndarray, feature_names: List[str]) -> Dict[int, Dict]:
        """Get average feature values for each cluster.

        Args:
            X (np.ndarray): Feature matrix.
            feature_names (List[str]): Names of features.

        Returns:
            Dict[int, Dict]: Dictionary of cluster profiles with average features.
        """
        profiles = {}
        
        for cluster_id in range(self.n_clusters):
            mask = self.labels_ == cluster_id
            if np.sum(mask) > 0:
                cluster_data = X[mask]
                profiles[cluster_id] = {
                    'name': EMOTIONAL_PROFILES.get(cluster_id, {}).get('name', f'Cluster {cluster_id}'),
                    'size': int(np.sum(mask)),
                    'avg_features': {
                        name: float(np.mean(cluster_data[:, i]))
                        for i, name in enumerate(feature_names)
                    }
                }
        
        return profiles
    
    def _save_model(self):
        """Save the fitted model to disk."""
        try:
            model_data = {
                'kmeans': self.kmeans,
                'scaler': self.scaler,
                'pca': self.pca,
                'cluster_centers': self.cluster_centers_,
                'user_profiles': self.user_profiles,
                'n_clusters': self.n_clusters,
                'feature_names': self.feature_extractor.feature_names,
                'saved_at': datetime.utcnow().isoformat()
            }
            
            model_file = self.model_path / "emotional_profile_model.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {model_file}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _load_model(self) -> bool:
        """Load a previously fitted model from disk.

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """
        try:
            model_file = self.model_path / "emotional_profile_model.pkl"
            if not model_file.exists():
                return False
            
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.kmeans = model_data['kmeans']
            self.scaler = model_data['scaler']
            self.pca = model_data['pca']
            self.cluster_centers_ = model_data['cluster_centers']
            self.user_profiles = model_data['user_profiles']
            self.n_clusters = model_data['n_clusters']
            self.is_fitted = True
            
            logger.info(f"Model loaded from {model_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


# ==============================================================================
# VISUALIZATION
# ==============================================================================

class ClusteringVisualizer:
    """Visualization tools for emotional profile clustering."""
    
    def __init__(self, clusterer: EmotionalProfileClusterer):
        """Initialize the visualizer with a clusterer instance.

        Args:
            clusterer (EmotionalProfileClusterer): The fitted clusterer to visualize.
        """
        self.clusterer = clusterer
    
    def plot_cluster_distribution(self, save_path: Optional[str] = None):
        """Plot the distribution of users across clusters.

        Args:
            save_path (Optional[str], optional): Path to save the plot. If None, plot is not saved.

        Returns:
            matplotlib.figure.Figure or None: The figure object if matplotlib is available, None otherwise.
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available for visualization")
            return None
        
        distribution = self.clusterer._get_cluster_distribution()
        if not distribution:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        clusters = list(distribution.keys())
        counts = list(distribution.values())
        colors = [EMOTIONAL_PROFILES.get(c, {}).get('color', '#999999') for c in clusters]
        labels = [EMOTIONAL_PROFILES.get(c, {}).get('name', f'Cluster {c}') for c in clusters]
        
        bars = ax.bar(labels, counts, color=colors, edgecolor='black', linewidth=1.2)
        
        ax.set_xlabel('Emotional Profile', fontsize=12)
        ax.set_ylabel('Number of Users', fontsize=12)
        ax.set_title('Distribution of Users Across Emotional Profiles', fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.annotate(f'{count}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=11)
        
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Cluster distribution plot saved to {save_path}")
        
        return fig
    
    def plot_pca_clusters(self, results: Dict, save_path: Optional[str] = None):
        """Plot PCA visualization of clusters.

        Args:
            results (Dict): Clustering results containing PCA coordinates and labels.
            save_path (Optional[str], optional): Path to save the plot. If None, plot is not saved.

        Returns:
            matplotlib.figure.Figure or None: The figure object if matplotlib is available, None otherwise.
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available for visualization")
            return None
        
        if 'pca_coordinates' not in results or not results['pca_coordinates']:
            return None
        
        pca_coords = np.array(results['pca_coordinates'])
        labels = np.array(results['labels'])
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for cluster_id in range(self.clusterer.n_clusters):
            mask = labels == cluster_id
            if np.sum(mask) > 0:
                profile = EMOTIONAL_PROFILES.get(cluster_id, {})
                ax.scatter(
                    pca_coords[mask, 0],
                    pca_coords[mask, 1],
                    c=profile.get('color', '#999999'),
                    label=f"{profile.get('emoji', '')} {profile.get('name', f'Cluster {cluster_id}')}",
                    s=100,
                    alpha=0.7,
                    edgecolors='black',
                    linewidth=0.5
                )
        
        ax.set_xlabel('Principal Component 1', fontsize=12)
        ax.set_ylabel('Principal Component 2', fontsize=12)
        ax.set_title('Emotional Profile Clusters (PCA Visualization)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"PCA cluster plot saved to {save_path}")
        
        return fig
    
    def plot_feature_radar(self, cluster_profiles: Dict, save_path: Optional[str] = None):
        """Plot radar chart comparing cluster feature profiles.

        Args:
            cluster_profiles (Dict): Dictionary of cluster profiles with average features.
            save_path (Optional[str], optional): Path to save the plot. If None, plot is not saved.

        Returns:
            matplotlib.figure.Figure or None: The figure object if matplotlib is available, None otherwise.
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available for visualization")
            return None
        
        if not cluster_profiles:
            return None
        
        # Get feature names from first cluster
        first_cluster = list(cluster_profiles.values())[0]
        if 'avg_features' not in first_cluster:
            return None
        
        features = list(first_cluster['avg_features'].keys())
        num_features = len(features)
        
        # Create angles for radar chart
        angles = np.linspace(0, 2 * np.pi, num_features, endpoint=False).tolist()
        angles += angles[:1]  # Close the loop
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        
        for cluster_id, profile in cluster_profiles.items():
            values = [profile['avg_features'].get(f, 0) for f in features]
            # Normalize values to 0-1 scale for visualization
            max_val = max(values) if max(values) > 0 else 1
            values_normalized = [v / max_val for v in values]
            values_normalized += values_normalized[:1]  # Close the loop
            
            profile_info = EMOTIONAL_PROFILES.get(cluster_id, {})
            ax.plot(
                angles, values_normalized,
                'o-', linewidth=2,
                label=profile_info.get('name', f'Cluster {cluster_id}'),
                color=profile_info.get('color', '#999999')
            )
            ax.fill(angles, values_normalized, alpha=0.25, color=profile_info.get('color', '#999999'))
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(features, size=9)
        ax.set_title('Emotional Profile Feature Comparison', fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Feature radar plot saved to {save_path}")
        
        return fig
    
    def generate_profile_report(self, username: str) -> str:
        """Generate a text report for a user's emotional profile.

        Args:
            username (str): Username to generate report for.

        Returns:
            str: Formatted text report of the user's emotional profile.
        """
        profile = self.clusterer.get_user_profile(username)
        
        if not profile:
            return f"No profile data available for user: {username}"
        
        profile_info = profile.get('profile', {})
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║          EMOTIONAL PROFILE REPORT                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ User: {username:<55} ║
║ Profile: {profile_info.get('emoji', '')} {profile_info.get('name', 'Unknown'):<51} ║
║ Confidence: {profile.get('confidence', 0)*100:.1f}%{' ':<48}║
╠══════════════════════════════════════════════════════════════════╣
║ DESCRIPTION                                                       ║
╠══════════════════════════════════════════════════════════════════╣
"""
        
        desc = profile_info.get('description', 'No description available')
        report += f"║ {desc:<64} ║\n"
        
        report += """╠══════════════════════════════════════════════════════════════════╣
║ KEY CHARACTERISTICS                                               ║
╠══════════════════════════════════════════════════════════════════╣
"""
        
        for char in profile_info.get('characteristics', []):
            report += f"║ • {char:<62} ║\n"
        
        report += """╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDATIONS                                                   ║
╠══════════════════════════════════════════════════════════════════╣
"""
        
        for rec in profile_info.get('recommendations', []):
            report += f"║ → {rec:<62} ║\n"
        
        report += "╚══════════════════════════════════════════════════════════════════╝"
        
        return report


# ==============================================================================
# INTEGRATION HELPERS
# ==============================================================================

def create_profile_clusterer(n_clusters: int = 4) -> EmotionalProfileClusterer:
    """Factory function to create a profile clusterer.

    Args:
        n_clusters (int, optional): Number of clusters. Defaults to 4.

    Returns:
        EmotionalProfileClusterer: Initialized clusterer instance.
    """
    return EmotionalProfileClusterer(n_clusters=n_clusters)


def cluster_all_users(n_clusters: int = 4) -> Dict[str, Any]:
    """Convenience function to cluster all users in the database.

    Args:
        n_clusters (int, optional): Number of clusters. Defaults to 4.

    Returns:
        Dict[str, Any]: Clustering results.
    """
    clusterer = create_profile_clusterer(n_clusters)
    return clusterer.fit()


def get_user_emotional_profile(username: str) -> Optional[Dict[str, Any]]:
    """Get emotional profile for a specific user.

    Args:
        username (str): Username to get profile for.

    Returns:
        Optional[Dict[str, Any]]: User's emotional profile data.
    """
    clusterer = create_profile_clusterer()
    return clusterer.predict(username)


def get_profile_summary() -> Dict[str, Any]:
    """Get summary of all emotional profiles.

    Returns:
        Dict[str, Any]: Summary including profiles, distribution, and total users.
    """
    clusterer = create_profile_clusterer()
    
    if not clusterer._load_model():
        # Need to fit first
        results = clusterer.fit()
        if 'error' in results:
            return results
    
    return {
        'profiles': EMOTIONAL_PROFILES,
        'distribution': clusterer._get_cluster_distribution(),
        'total_users': len(clusterer.user_profiles)
    }


# ==============================================================================
# CLI INTERFACE
# ==============================================================================

def main():
    """Main CLI entry point for emotional profile clustering."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Emotional Profile Clustering for SoulSense',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python emotional_profile_clustering.py --fit                    # Cluster all users
  python emotional_profile_clustering.py --predict <username>     # Predict user profile
  python emotional_profile_clustering.py --summary                # Show profile summary
  python emotional_profile_clustering.py --visualize              # Generate visualizations
        """
    )
    
    parser.add_argument('--fit', action='store_true', help='Fit clustering model on all users')
    parser.add_argument('--predict', type=str, metavar='USERNAME', help='Predict profile for a user')
    parser.add_argument('--summary', action='store_true', help='Show profile summary')
    parser.add_argument('--visualize', action='store_true', help='Generate cluster visualizations')
    parser.add_argument('--n-clusters', type=int, default=4, help='Number of clusters (default: 4)')
    parser.add_argument('--output-dir', type=str, default='outputs/clustering', help='Output directory for visualizations')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    clusterer = create_profile_clusterer(n_clusters=args.n_clusters)
    visualizer = ClusteringVisualizer(clusterer)
    
    if args.fit:
        print("\n🔄 Fitting emotional profile clustering model...")
        results = clusterer.fit()
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        print(f"\n✅ Clustering Complete!")
        print(f"   • Users clustered: {results['n_users']}")
        print(f"   • Number of profiles: {results['n_clusters']}")
        print(f"   • Silhouette score: {results['metrics'].get('silhouette_score', 0):.3f}")
        
        print("\n📊 Cluster Distribution:")
        for cluster_id, count in results['cluster_distribution'].items():
            profile = EMOTIONAL_PROFILES.get(cluster_id, {})
            print(f"   {profile.get('emoji', '')} {profile.get('name', f'Cluster {cluster_id}')}: {count} users")
    
    elif args.predict:
        print(f"\n🔍 Predicting profile for user: {args.predict}")
        profile = clusterer.predict(args.predict)
        
        if not profile:
            print(f"❌ Could not predict profile for user: {args.predict}")
            return
        
        report = visualizer.generate_profile_report(args.predict)
        print(report)
    
    elif args.summary:
        print("\n📈 Emotional Profile Summary")
        summary = get_profile_summary()
        
        if 'error' in summary:
            print(f"❌ Error: {summary['error']}")
            return
        
        print(f"\n   Total users profiled: {summary.get('total_users', 0)}")
        print("\n   Profile Distribution:")
        for cluster_id, count in summary.get('distribution', {}).items():
            profile = EMOTIONAL_PROFILES.get(cluster_id, {})
            print(f"   {profile.get('emoji', '')} {profile.get('name', f'Cluster {cluster_id}')}: {count}")
    
    elif args.visualize:
        if not MATPLOTLIB_AVAILABLE:
            print("❌ Matplotlib not available. Install with: pip install matplotlib")
            return
        
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n📊 Generating visualizations...")
        
        # Fit if not already fitted
        results = clusterer.fit()
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        # Generate plots
        visualizer.plot_cluster_distribution(
            save_path=str(output_dir / 'cluster_distribution.png')
        )
        visualizer.plot_pca_clusters(
            results,
            save_path=str(output_dir / 'pca_clusters.png')
        )
        visualizer.plot_feature_radar(
            results.get('cluster_profiles', {}),
            save_path=str(output_dir / 'feature_radar.png')
        )
        
        print(f"✅ Visualizations saved to: {output_dir}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
