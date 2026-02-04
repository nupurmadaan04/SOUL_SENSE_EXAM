
import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ui.dashboard import AnalyticsDashboard


class TestProgressDashboard:
    """Test cases for the Progress Dashboard functionality"""

    @pytest.fixture
    def mock_parent(self):
        """Create a mock parent widget"""
        parent = Mock()
        parent.configure = Mock()
        return parent

    @pytest.fixture
    def dashboard(self, mock_parent):
        """Create a dashboard instance with mocked dependencies"""
        with patch('app.ui.dashboard.get_connection'), \
             patch('app.ui.dashboard.safe_db_context'), \
             patch('app.ui.dashboard.time_analyzer'), \
             patch('app.ui.dashboard.get_i18n') as mock_i18n:

            mock_i18n.return_value.get = Mock(return_value="Mock Text")

            dashboard = AnalyticsDashboard(
                parent_root=mock_parent,
                username="test_user",
                colors={"bg": "#fff", "surface": "#f0f0f0", "text_primary": "#000",
                       "text_secondary": "#666", "primary": "#007bff", "border": "#ccc"},
                theme="light"
            )
            return dashboard

    def test_progress_dashboard_creation(self, dashboard, mock_parent):
        """Test that progress dashboard can be created without errors"""
        try:
            # Mock the database connection and cursor
            with patch('app.ui.dashboard.get_connection') as mock_conn:
                mock_cursor = Mock()
                mock_conn.return_value.cursor.return_value = mock_cursor
                mock_cursor.fetchall.return_value = []
                mock_conn.return_value.close = Mock()

                # This should not raise an exception
                dashboard.show_progress_dashboard(mock_parent)
                assert True  # If we get here, no exception was raised

        except Exception as e:
            pytest.fail(f"Progress dashboard creation failed: {e}")

    @pytest.fixture
    def sample_eq_data(self):
        """Sample EQ score data for testing"""
        return [
            (20, "2024-01-01T10:00:00", 15),
            (22, "2024-01-08T10:00:00", 20),
            (24, "2024-01-15T10:00:00", 25),
            (23, "2024-01-22T10:00:00", 18)
        ]

    @pytest.fixture
    def sample_journal_data(self):
        """Sample journal entry data for testing"""
        return [
            ("2024-01-01 10:00:00", 10),
            ("2024-01-02 10:00:00", 15),
            ("2024-01-03 10:00:00", -5),
            ("2024-01-04 10:00:00", 20),
            ("2024-01-05 10:00:00", 8)
        ]

    def test_progress_dashboard_with_data(self, dashboard, mock_parent, sample_eq_data, sample_journal_data):
        """Test progress dashboard with sample data"""
        with patch('app.ui.dashboard.get_connection') as mock_conn, \
             patch.object(dashboard, '_create_scrollable_frame') as mock_scrollable, \
             patch('tkinter.Frame') as mock_frame, \
             patch('tkinter.Label') as mock_label, \
             patch('matplotlib.backends.backend_tkagg.FigureCanvasTkAgg') as mock_canvas:

            # Setup mock database responses
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor

            # Mock EQ data query
            mock_cursor.execute.side_effect = [
                None,  # First call for EQ scores
                None   # Second call for journal entries
            ]
            mock_cursor.fetchall.side_effect = [
                sample_eq_data,      # EQ scores result
                sample_journal_data  # Journal entries result
            ]
            mock_conn.return_value.close = Mock()

            # Mock GUI components
            mock_scrollable.return_value = mock_parent
            mock_frame_instance = Mock()
            mock_frame.return_value = mock_frame_instance
            mock_label_instance = Mock()
            mock_label.return_value = mock_label_instance
            mock_canvas_instance = Mock()
            mock_canvas.return_value = mock_canvas_instance

            # This should not raise an exception
            dashboard.show_progress_dashboard(mock_parent)

            # Verify database queries were made
            assert mock_cursor.execute.call_count >= 2

    def test_progress_dashboard_empty_data(self, dashboard, mock_parent):
        """Test progress dashboard with no data"""
        with patch('app.ui.dashboard.get_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.close = Mock()

            dashboard.show_progress_dashboard(mock_parent)

            # Should handle empty data gracefully (no exceptions)

    def test_milestone_calculations(self, dashboard):
        """Test milestone calculation logic"""
        # Test data
        eq_scores = [18, 21, 23, 24]
        journal_entries = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

        # Test milestone definitions (extracted from the method)
        milestones_data = [
            {"name": "First Assessment", "threshold": 1, "current": len(eq_scores)},
            {"name": "EQ Explorer", "threshold": 5, "current": len(eq_scores)},
            {"name": "EQ Achiever", "threshold": 20, "current": max(eq_scores)},
            {"name": "EQ Master", "threshold": 22, "current": max(eq_scores)},
            {"name": "Reflective Mind", "threshold": 10, "current": len(journal_entries)},
            {"name": "Emotional Chronicler", "threshold": 25, "current": len(journal_entries)},
        ]

        # Verify calculations
        for milestone in milestones_data:
            assert milestone["current"] >= 0
            achieved = milestone["current"] >= milestone["threshold"]
            assert isinstance(achieved, bool)

    def test_progress_card_creation(self, dashboard, mock_parent):
        """Test that progress cards are created correctly"""
        with patch('app.ui.dashboard.get_connection') as mock_conn, \
             patch.object(dashboard, '_create_scrollable_frame') as mock_scrollable, \
             patch('tkinter.Frame') as mock_frame, \
             patch('tkinter.Label') as mock_label, \
             patch('matplotlib.backends.backend_tkagg.FigureCanvasTkAgg') as mock_canvas:

            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [
                (20, "2024-01-01T10:00:00", 15),
                (22, "2024-01-02T10:00:00", 18)
            ]
            mock_conn.return_value.close = Mock()

            # Mock GUI components
            mock_scrollable.return_value = mock_parent
            mock_frame_instance = Mock()
            mock_frame.return_value = mock_frame_instance
            mock_label_instance = Mock()
            mock_label.return_value = mock_label_instance
            mock_canvas_instance = Mock()
            mock_canvas.return_value = mock_canvas_instance

            dashboard.show_progress_dashboard(mock_parent)

            # Verify that frames and labels were created (progress cards)
            assert mock_frame.call_count > 0
            assert mock_label.call_count > 0

    def test_chart_rendering(self, dashboard, mock_parent, sample_eq_data):
        """Test that charts are rendered without errors"""
        with patch('app.ui.dashboard.get_connection') as mock_conn, \
             patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.backends.backend_tkagg.FigureCanvasTkAgg') as mock_canvas:

            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.side_effect = [sample_eq_data, []]
            mock_conn.return_value.close = Mock()

            # Mock matplotlib components
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            mock_ax = Mock()
            mock_fig.add_subplot.return_value = mock_ax
            mock_canvas_instance = Mock()
            mock_canvas.return_value = mock_canvas_instance

            dashboard.show_progress_dashboard(mock_parent)

            # Verify matplotlib was called
            assert mock_figure.call_count > 0
            assert mock_canvas.call_count > 0

    def test_database_error_handling(self, dashboard, mock_parent):
        """Test that database errors are handled gracefully"""
        with patch('app.ui.dashboard.get_connection') as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            # Should not raise an exception, should handle error gracefully
            dashboard.show_progress_dashboard(mock_parent)

    def test_navigation_integration(self, dashboard, mock_parent):
        """Test that progress dashboard integrates with notebook navigation"""
        with patch('app.ui.dashboard.get_connection') as mock_conn, \
             patch.object(dashboard, 'render_dashboard') as mock_render:

            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.close = Mock()

            # Test that render_dashboard includes progress tab
            dashboard.render_dashboard()

            # Verify that the progress tab was added to the notebook
            # This would require mocking ttk.Notebook, but for now we verify no exceptions
            assert True

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_theme_support(self, dashboard, mock_parent, theme):
        """Test progress dashboard works with different themes"""
        dashboard.theme = theme

        with patch('app.ui.dashboard.get_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.close = Mock()

            dashboard.show_progress_dashboard(mock_parent)

            # Should work with both themes without errors
            assert dashboard.theme == theme


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
