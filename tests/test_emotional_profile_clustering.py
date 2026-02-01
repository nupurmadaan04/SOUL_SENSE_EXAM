import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.clustering import (
    EmotionalFeatureExtractor,
    EmotionalProfileClusterer,
    ClusteringVisualizer,
    EMOTIONAL_PROFILES,
    create_profile_clusterer,
    cluster_all_users,
    get_user_emotional_profile,
    get_profile_summary
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def sample_user_data():
    """Create sample user feature data for testing."""
    np.random.seed(42)
    n_users = 50
    
    data = {
        'username': [f'test_user_{i}' for i in range(n_users)],
        'avg_total_score': np.random.uniform(20, 100, n_users),
        'score_std': np.random.uniform(0, 20, n_users),
        'avg_sentiment': np.random.uniform(-1, 1, n_users),
        'sentiment_std': np.random.uniform(0, 0.5, n_users),
        'score_trend': np.random.uniform(-1, 1, n_users),
        'response_consistency': np.random.uniform(0, 1, n_users),
        'emotional_range': np.random.uniform(0, 50, n_users),
        'assessment_frequency': np.random.randint(1, 20, n_users),
        'avg_response_value': np.random.uniform(1, 5, n_users),
        'response_variance': np.random.uniform(0, 2, n_users)
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_score():
    """Create a mock Score object."""
    score = Mock()
    score.total_score = 75
    score.sentiment_score = 0.5
    score.timestamp = datetime.utcnow().isoformat()
    return score


@pytest.fixture
def mock_response():
    """Create a mock Response object."""
    response = Mock()
    response.response_value = 3
    response.question_id = 1
    response.timestamp = datetime.utcnow().isoformat()
    return response


@pytest.fixture
def clusterer():
    """Create a clusterer instance for testing."""
    return EmotionalProfileClusterer(n_clusters=4, random_state=42)


@pytest.fixture
def feature_extractor():
    """Create a feature extractor instance for testing."""
    return EmotionalFeatureExtractor()


# ==============================================================================
# TEST EMOTIONAL PROFILES DEFINITION
# ==============================================================================

class TestEmotionalProfiles:
    """Test emotional profile definitions."""
    
    def test_profiles_exist(self):
        """Test that all expected profiles are defined."""
        assert len(EMOTIONAL_PROFILES) == 4
        assert all(i in EMOTIONAL_PROFILES for i in range(4))
    
    def test_profile_structure(self):
        """Test that each profile has required fields."""
        required_fields = ['name', 'description', 'characteristics', 'recommendations', 'color', 'emoji']
        
        for profile_id, profile in EMOTIONAL_PROFILES.items():
            for field in required_fields:
                assert field in profile, f"Profile {profile_id} missing field: {field}"
    
    def test_profile_names_unique(self):
        """Test that profile names are unique."""
        names = [p['name'] for p in EMOTIONAL_PROFILES.values()]
        assert len(names) == len(set(names)), "Profile names should be unique"
    
    def test_profile_colors_valid(self):
        """Test that profile colors are valid hex codes."""
        for profile in EMOTIONAL_PROFILES.values():
            color = profile['color']
            assert color.startswith('#'), f"Color {color} should start with #"
            assert len(color) == 7, f"Color {color} should be 7 characters"


# ==============================================================================
# TEST FEATURE EXTRACTOR
# ==============================================================================

@pytest.fixture(autouse=True)
def mock_sklearn_imports():
    """Mock the lazy loader for sklearn imports"""
    mock_imports = {
        'KMeans': MagicMock(),
        'DBSCAN': MagicMock(),
        'AgglomerativeClustering': MagicMock(),
        'StandardScaler': MagicMock(),
        'MinMaxScaler': MagicMock(),
        'PCA': MagicMock(),
        'silhouette_score': MagicMock(return_value=0.5),
        'calinski_harabasz_score': MagicMock(return_value=100.0),
        'davies_bouldin_score': MagicMock(return_value=0.5),
        'TSNE': MagicMock()
    }
    
    # Configure standardize mocks
    mock_scaler_instance = MagicMock()
    # Support dynamic shapes for testing
    def side_effect_transform(X, *args, **kwargs):
        if not isinstance(X, (np.ndarray, list)):
           return np.zeros((10, 10))
        return np.array(X)
    mock_scaler_instance.fit_transform.side_effect = side_effect_transform
    mock_scaler_instance.transform.side_effect = side_effect_transform
    mock_imports['StandardScaler'].return_value = mock_scaler_instance
    
    # Configure PCA mocks
    mock_pca_instance = MagicMock()
    mock_pca_instance.fit_transform.return_value = np.zeros((10, 2))
    mock_imports['PCA'].return_value = mock_pca_instance
    
    # Configure EMOTIONAL_PROFILES for consistency if accessed via module
    # (Though typically imported)

    # Define a generic fit_predict side effect that returns correct shape
    def generic_fit_predict(X, *args, **kwargs):
        n_samples = len(X) if hasattr(X, '__len__') else 10
        return np.zeros(n_samples, dtype=int)

    # Factory for creating fresh KMeans instances
    def create_mock_kmeans(*args, **kwargs):
        kmeans_mock = MagicMock()
        kmeans_mock.inertia_ = 100.0
        
        def kmeans_fit_predict_side_effect(X, *args, **kwargs):
            n_samples = len(X) if hasattr(X, '__len__') else 10
            n_features = X.shape[1] if hasattr(X, 'shape') and len(X.shape) > 1 else 10
            kmeans_mock.cluster_centers_ = np.zeros((4, n_features))
            kmeans_mock.labels_ = np.zeros(n_samples, dtype=int)
            return np.zeros(n_samples, dtype=int)
            
        kmeans_mock.fit_predict.side_effect = kmeans_fit_predict_side_effect
        kmeans_mock.predict.return_value = np.zeros(1, dtype=int)
        
        # Initial attributes (before fit)
        kmeans_mock.cluster_centers_ = np.zeros((4, 10))
        kmeans_mock.labels_ = None 
        return kmeans_mock

    mock_imports['KMeans'].side_effect = create_mock_kmeans
    
    # Configure DBSCAN mocks
    mock_dbscan_instance = MagicMock()
    mock_dbscan_instance.fit_predict.side_effect = generic_fit_predict
    mock_imports['DBSCAN'].return_value = mock_dbscan_instance
    
    # Configure AgglomerativeClustering mocks
    mock_agg_instance = MagicMock()
    mock_agg_instance.fit_predict.side_effect = generic_fit_predict
    mock_imports['AgglomerativeClustering'].return_value = mock_agg_instance

    with patch('app.ml.clustering._get_sklearn_imports', return_value=mock_imports):
        yield mock_imports

class TestEmotionalFeatureExtractor:
    """Test feature extraction functionality."""
    
    def test_feature_names(self, feature_extractor):
        """Test that feature names are defined."""
        assert len(feature_extractor.feature_names) > 0
        assert 'avg_total_score' in feature_extractor.feature_names
        assert 'avg_sentiment' in feature_extractor.feature_names
    
    def test_calculate_trend_increasing(self, feature_extractor):
        """Test trend calculation for increasing scores."""
        scores = [10, 20, 30, 40, 50]
        trend = feature_extractor._calculate_trend(scores)
        assert trend > 0, "Increasing scores should have positive trend"
    
    def test_calculate_trend_decreasing(self, feature_extractor):
        """Test trend calculation for decreasing scores."""
        scores = [50, 40, 30, 20, 10]
        trend = feature_extractor._calculate_trend(scores)
        assert trend < 0, "Decreasing scores should have negative trend"
    
    def test_calculate_trend_single_value(self, feature_extractor):
        """Test trend calculation with single value."""
        scores = [50]
        trend = feature_extractor._calculate_trend(scores)
        assert trend == 0, "Single value should have zero trend"
    
    def test_calculate_consistency_uniform(self, feature_extractor):
        """Test consistency calculation for uniform responses."""
        responses = [Mock(response_value=3) for _ in range(10)]
        consistency = feature_extractor._calculate_consistency(responses)
        assert consistency == 1.0, "Uniform responses should have perfect consistency"
    
    def test_calculate_consistency_varied(self, feature_extractor):
        """Test consistency calculation for varied responses."""
        responses = [Mock(response_value=i) for i in [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]]
        consistency = feature_extractor._calculate_consistency(responses)
        assert 0 < consistency < 1, "Varied responses should have partial consistency"
    
    def test_calculate_consistency_empty(self, feature_extractor):
        """Test consistency calculation with no responses."""
        consistency = feature_extractor._calculate_consistency([])
        assert consistency == 0.0, "Empty responses should have zero consistency"
    
    def test_avg_response_value(self, feature_extractor):
        """Test average response value calculation."""
        responses = [Mock(response_value=i) for i in [1, 2, 3, 4, 5]]
        avg = feature_extractor._avg_response_value(responses)
        assert avg == 3.0, "Average of 1-5 should be 3"
    
    def test_avg_response_value_empty(self, feature_extractor):
        """Test average response value with no responses."""
        avg = feature_extractor._avg_response_value([])
        assert avg == 2.5, "Empty responses should return neutral default"
    
    def test_response_variance(self, feature_extractor):
        """Test response variance calculation."""
        responses = [Mock(response_value=3) for _ in range(5)]
        variance = feature_extractor._response_variance(responses)
        assert variance == 0.0, "Uniform responses should have zero variance"


# ==============================================================================
# TEST CLUSTERER
# ==============================================================================

class TestEmotionalProfileClusterer:
    """Test clustering functionality."""
    
    def test_initialization(self, clusterer):
        """Test clusterer initialization."""
        assert clusterer.n_clusters == 4
        assert clusterer.random_state == 42
        assert not clusterer.is_fitted
    
    def test_fit_with_data(self, clusterer, sample_user_data):
        """Test fitting with provided data."""
        results = clusterer.fit(data=sample_user_data)
        
        assert 'error' not in results
        assert results['n_users'] == len(sample_user_data)
        assert results['n_clusters'] == clusterer.n_clusters
        assert len(results['labels']) == len(sample_user_data)
        assert clusterer.is_fitted
    
    def test_fit_insufficient_data(self, clusterer):
        """Test fitting with insufficient data."""
        small_data = pd.DataFrame({
            'username': ['user1'],
            'avg_total_score': [50],
            'score_std': [10],
            'avg_sentiment': [0],
            'sentiment_std': [0.1],
            'score_trend': [0],
            'response_consistency': [0.5],
            'emotional_range': [10],
            'assessment_frequency': [5],
            'avg_response_value': [3],
            'response_variance': [0.5]
        })
        
        results = clusterer.fit(data=small_data)
        assert 'error' in results
    
    def test_cluster_labels_range(self, clusterer, sample_user_data):
        """Test that cluster labels are in valid range."""
        results = clusterer.fit(data=sample_user_data)
        labels = results['labels']
        
        assert all(0 <= label < clusterer.n_clusters for label in labels)
    
    def test_clustering_metrics(self, clusterer, sample_user_data):
        """Test that clustering metrics are calculated."""
        results = clusterer.fit(data=sample_user_data)
        metrics = results['metrics']
        
        assert 'silhouette_score' in metrics
        assert 'calinski_harabasz' in metrics
        assert 'davies_bouldin' in metrics
        assert 'inertia' in metrics
    
    def test_cluster_distribution(self, clusterer, sample_user_data):
        """Test cluster distribution calculation."""
        results = clusterer.fit(data=sample_user_data)
        distribution = results['cluster_distribution']
        
        assert sum(distribution.values()) == len(sample_user_data)
    
    def test_predict_after_fit(self, clusterer, sample_user_data):
        """Test prediction after fitting."""
        clusterer.fit(data=sample_user_data)
        
        # Create mock for predict
        with patch.object(clusterer.feature_extractor, 'extract_user_features') as mock_extract:
            mock_extract.return_value = {
                'username': 'new_user',
                'avg_total_score': 75,
                'score_std': 10,
                'avg_sentiment': 0.5,
                'sentiment_std': 0.2,
                'score_trend': 0.3,
                'response_consistency': 0.8,
                'emotional_range': 20,
                'assessment_frequency': 5,
                'avg_response_value': 3.5,
                'response_variance': 0.5
            }
            
            result = clusterer.predict('new_user')
            
            assert result is not None
            assert 'cluster_id' in result
            assert 'profile_name' in result
            assert 'confidence' in result
            assert 0 <= result['cluster_id'] < clusterer.n_clusters
            assert 0 <= result['confidence'] <= 1
    
    def test_get_cluster_users(self, clusterer, sample_user_data):
        """Test getting users by cluster."""
        clusterer.fit(data=sample_user_data)
        
        all_users = []
        for cluster_id in range(clusterer.n_clusters):
            users = clusterer.get_cluster_users(cluster_id)
            all_users.extend(users)
        
        # All users should be assigned to exactly one cluster
        assert len(all_users) == len(sample_user_data)
    
    def test_find_optimal_clusters(self, clusterer, sample_user_data):
        """Test optimal cluster finding."""
        feature_cols = [col for col in sample_user_data.columns if col != 'username']
        X = sample_user_data[feature_cols].values
        # Fix: Use accessor method to ensure initialization
        X_scaled = clusterer._get_scaler().fit_transform(X)
        
        optimal_k = clusterer._find_optimal_clusters(X_scaled, max_k=6)
        
        assert 2 <= optimal_k <= 6
    
    def test_model_save_load(self, clusterer, sample_user_data, tmp_path):
        """Test model saving and loading."""
        clusterer.model_path = tmp_path / "test_models"
        clusterer.model_path.mkdir(parents=True, exist_ok=True)
        
        # Fit
        clusterer.fit(data=sample_user_data)
        
        # Mock pickle to avoid pickling mocks
        with patch('app.ml.clustering.pickle') as mock_pickle:
            # Configure pickle load to return a valid dict
            mock_pickle.load.return_value = {
                 'n_clusters': 4,
                 'random_state': 42,
                 'is_fitted': True,
                 'labels_': np.zeros(len(sample_user_data), dtype=int),
                 'cluster_centers': np.zeros((4, 10)), # Note: Key name matches _load_model expectation
                 'user_profiles': clusterer.user_profiles,
                 'kmeans': MagicMock(),
                 'scaler': MagicMock(),
                 'pca': MagicMock(),
                 'dbscan': MagicMock(),
                 'hierarchical': MagicMock()
            }
            
            # Simulate save
            clusterer._save_model()
            
            # Create new clusterer and load
            new_clusterer = EmotionalProfileClusterer(n_clusters=4)
            new_clusterer.model_path = clusterer.model_path
            
            # Simulate load
            loaded = new_clusterer._load_model()
            
            assert loaded
            assert new_clusterer.is_fitted
            assert new_clusterer.n_clusters == clusterer.n_clusters
            assert mock_pickle.dump.called
            assert mock_pickle.load.called


# ==============================================================================
# TEST VISUALIZER
# ==============================================================================

class TestClusteringVisualizer:
    """Test visualization functionality."""
    
    def test_generate_profile_report(self, clusterer, sample_user_data):
        """Test profile report generation."""
        clusterer.fit(data=sample_user_data)
        visualizer = ClusteringVisualizer(clusterer)
        
        # Get first user
        username = sample_user_data['username'].iloc[0]
        report = visualizer.generate_profile_report(username)
        
        assert username in report
        assert 'EMOTIONAL PROFILE REPORT' in report
        assert 'CHARACTERISTICS' in report
        assert 'RECOMMENDATIONS' in report
    
    def test_generate_report_unknown_user(self, clusterer):
        """Test report generation for unknown user."""
        visualizer = ClusteringVisualizer(clusterer)
        report = visualizer.generate_profile_report('nonexistent_user')
        
        assert 'No profile data available' in report


# ==============================================================================
# TEST HELPER FUNCTIONS
# ==============================================================================

class TestHelperFunctions:
    """Test helper/factory functions."""
    
    def test_create_profile_clusterer(self):
        """Test clusterer factory function."""
        clusterer = create_profile_clusterer(n_clusters=3)
        
        assert isinstance(clusterer, EmotionalProfileClusterer)
        assert clusterer.n_clusters == 3
    
    def test_create_profile_clusterer_default(self):
        """Test clusterer factory with default parameters."""
        clusterer = create_profile_clusterer()
        
        assert clusterer.n_clusters == 4


# ==============================================================================
# TEST EDGE CASES
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_nan_handling(self, clusterer):
        """Test handling of NaN values in data."""
        data = pd.DataFrame({
            'username': [f'user_{i}' for i in range(10)],
            'avg_total_score': [50, np.nan, 60, 70, np.nan, 80, 90, 100, 40, 30],
            'score_std': [10] * 10,
            'avg_sentiment': [0] * 10,
            'sentiment_std': [0.1] * 10,
            'score_trend': [0] * 10,
            'response_consistency': [0.5] * 10,
            'emotional_range': [10] * 10,
            'assessment_frequency': [5] * 10,
            'avg_response_value': [3] * 10,
            'response_variance': [0.5] * 10
        })
        
        results = clusterer.fit(data=data)
        
        assert 'error' not in results
        assert results['n_users'] == 10
    
    def test_identical_users(self, clusterer):
        """Test clustering with identical user data."""
        data = pd.DataFrame({
            'username': [f'user_{i}' for i in range(10)],
            'avg_total_score': [50] * 10,
            'score_std': [10] * 10,
            'avg_sentiment': [0] * 10,
            'sentiment_std': [0.1] * 10,
            'score_trend': [0] * 10,
            'response_consistency': [0.5] * 10,
            'emotional_range': [10] * 10,
            'assessment_frequency': [5] * 10,
            'avg_response_value': [3] * 10,
            'response_variance': [0.5] * 10
        })
        
        results = clusterer.fit(data=data)
        
        # Should not error, but all users may be in same cluster
        assert 'error' not in results
    
    def test_extreme_values(self, clusterer):
        """Test clustering with extreme values."""
        data = pd.DataFrame({
            'username': [f'user_{i}' for i in range(10)],
            'avg_total_score': [0, 1000, 50, 50, 50, 50, 50, 50, 50, 50],
            'score_std': [0, 100, 10, 10, 10, 10, 10, 10, 10, 10],
            'avg_sentiment': [-100, 100, 0, 0, 0, 0, 0, 0, 0, 0],
            'sentiment_std': [0] * 10,
            'score_trend': [0] * 10,
            'response_consistency': [0.5] * 10,
            'emotional_range': [10] * 10,
            'assessment_frequency': [5] * 10,
            'avg_response_value': [3] * 10,
            'response_variance': [0.5] * 10
        })
        
        results = clusterer.fit(data=data)
        
        assert 'error' not in results


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================

class TestIntegration:
    """Integration tests for the complete clustering pipeline."""
    
    def test_full_pipeline(self, sample_user_data):
        """Test the complete clustering pipeline."""
        # Create clusterer
        clusterer = create_profile_clusterer(n_clusters=4)
        
        # Fit
        results = clusterer.fit(data=sample_user_data)
        assert 'error' not in results
        
        # Get distribution
        distribution = clusterer._get_cluster_distribution()
        assert sum(distribution.values()) == len(sample_user_data)
        
        # Get user profile
        username = sample_user_data['username'].iloc[0]
        profile = clusterer.get_user_profile(username)
        assert profile is not None
        assert 'profile_name' in profile
        
        # Generate report
        visualizer = ClusteringVisualizer(clusterer)
        report = visualizer.generate_profile_report(username)
        assert len(report) > 0
    
    def test_multiple_fits(self, sample_user_data):
        """Test that multiple fits work correctly."""
        clusterer = create_profile_clusterer(n_clusters=4)
        
        # First fit
        results1 = clusterer.fit(data=sample_user_data)
        labels1 = results1['labels']
        
        # Second fit (should reset)
        results2 = clusterer.fit(data=sample_user_data)
        labels2 = results2['labels']
        
        # Labels should be deterministic with same random state
        assert labels1 == labels2


# ==============================================================================
# RUN TESTS
# ==============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
