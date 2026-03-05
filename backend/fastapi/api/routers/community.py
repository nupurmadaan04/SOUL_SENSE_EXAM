from fastapi import APIRouter, HTTPException
from ..services.github_service import github_service

router = APIRouter(tags=["Community Dashboard"])

@router.get("/stats")
async def get_community_stats(refresh: bool = False):
    """Get aggregated repository statistics."""
    repo_stats = await github_service.get_repo_stats(refresh=refresh)
    
    # Only refresh PRs if stats refresh is requested (cascade effect)
    pr_stats = await github_service.get_pull_requests(refresh=refresh)
    
    return {
        "repository": repo_stats,
        "pull_requests": pr_stats
    }

@router.get("/contributors")
async def get_contributors(limit: int = 100, refresh: bool = False):
    """Get list of top contributors."""
    contributors = await github_service.get_contributors(limit, refresh=refresh)
    return contributors

@router.get("/activity")
async def get_activity(refresh: bool = False):
    """Get weekly commit activity for the past year."""
    activity = await github_service.get_activity(refresh=refresh)
    return activity

@router.get("/mix")
async def get_contribution_mix(refresh: bool = False):
    """Get contribution types breakdown."""
    return await github_service.get_contribution_mix(refresh=refresh)

@router.get("/reviews")
async def get_reviewer_stats(refresh: bool = False):
    """Get top reviewers and community sentiment."""
    return await github_service.get_reviewer_stats(refresh=refresh)

@router.get("/graph")
async def get_community_graph(refresh: bool = False):
    """Get force-directed graph data for contributor connections."""
    return await github_service.get_community_graph(refresh=refresh)

@router.get("/sunburst")
async def get_repository_sunburst(refresh: bool = False):
    """Get repository directory attention data for sunburst chart."""
    return await github_service.get_repository_sunburst(refresh=refresh)

@router.get("/pulse")
async def get_pulse_feed(limit: int = 15, refresh: bool = False):
    """Get recent repository activity for a live pulse feed."""
    return await github_service.get_pulse_feed(limit, refresh=refresh)

@router.get("/issues")
async def get_good_first_issues(refresh: bool = False):
    """Get beginner-friendly issues for new contributors."""
    return await github_service.get_good_first_issues(refresh=refresh)

@router.get("/roadmap")
async def get_project_roadmap(refresh: bool = False):
    """Get project milestones for the roadmap progress."""
    return await github_service.get_project_roadmap(refresh=refresh)

@router.get("/mission-control")
async def get_mission_control_data(refresh: bool = False):
    """Returns aggregated data for the Mission Control center (God's Eye View)."""
    return await github_service.get_mission_control_data(refresh=refresh)
