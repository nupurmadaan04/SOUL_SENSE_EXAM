import React, { useEffect, useState } from 'react';
import { useCachedApi } from '@/hooks/useCachedApi';

interface Badge {
  name: string;
  description: string;
  icon: string;
  category: string;
  progress: number;
  milestone: number;
  unlocked: boolean;
  earned_at: string | null;
}

export const BadgeDisplay: React.FC = () => {
  const { data: badges, isLoading } = useCachedApi<Badge[]>('/badges', { refreshInterval: 60000 });
  const [filter, setFilter] = useState<string>('all');

  const filteredBadges = badges?.filter(b => 
    filter === 'all' || 
    (filter === 'unlocked' && b.unlocked) || 
    (filter === 'locked' && !b.unlocked)
  ) || [];

  if (isLoading) return <div className="animate-pulse">Loading badges...</div>;

  return (
    <div className="badge-container">
      <div className="flex gap-2 mb-4">
        <button onClick={() => setFilter('all')} className={filter === 'all' ? 'active' : ''}>All</button>
        <button onClick={() => setFilter('unlocked')} className={filter === 'unlocked' ? 'active' : ''}>Unlocked</button>
        <button onClick={() => setFilter('locked')} className={filter === 'locked' ? 'active' : ''}>Locked</button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {filteredBadges.map((badge) => (
          <div 
            key={badge.name} 
            className={`badge-card ${badge.unlocked ? 'unlocked' : 'locked'}`}
          >
            <div className="badge-icon text-4xl">{badge.icon}</div>
            <h3 className="font-semibold mt-2">{badge.name.replace(/_/g, ' ')}</h3>
            <p className="text-sm text-gray-600">{badge.description}</p>
            
            {!badge.unlocked && (
              <div className="progress-bar mt-2">
                <div className="progress-fill" style={{ width: `${(badge.progress / badge.milestone) * 100}%` }} />
                <span className="text-xs">{badge.progress}/{badge.milestone}</span>
              </div>
            )}
            
            {badge.unlocked && badge.earned_at && (
              <p className="text-xs text-green-600 mt-2">
                Earned: {new Date(badge.earned_at).toLocaleDateString()}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
