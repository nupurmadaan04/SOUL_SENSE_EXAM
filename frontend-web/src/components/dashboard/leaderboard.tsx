import { useRef, useState, useEffect, useCallback } from 'react';
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
} from '@/components/ui';
import { motion, LayoutGroup } from 'framer-motion';
import {
  Trophy,
  Medal,
  Crown,
  ChevronLeft,
  ChevronRight,
  BarChart2,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { ContributorDetailsModal } from './contributor-details-modal';

export function Leaderboard({ contributors }: { contributors: any[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);
  const [selectedContributor, setSelectedContributor] = useState<any | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const checkScroll = useCallback(() => {
    if (scrollRef.current && !isExpanded) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
      setCanScrollLeft(scrollLeft > 10);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10);
    }
  }, [isExpanded]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && !isExpanded) {
      el.addEventListener('scroll', checkScroll);
      checkScroll();
      window.addEventListener('resize', checkScroll);
      return () => {
        el.removeEventListener('scroll', checkScroll);
        window.removeEventListener('resize', checkScroll);
      };
    }
  }, [contributors, isExpanded, checkScroll]);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 300;
      const target =
        direction === 'left'
          ? scrollRef.current.scrollLeft - scrollAmount
          : scrollRef.current.scrollLeft + scrollAmount;

      scrollRef.current.scrollTo({
        left: target,
        behavior: 'smooth',
      });
    }
  };

  const getRankIcon = (index: number) => {
    switch (index) {
      case 0:
        return <Crown className="h-4 w-4 text-yellow-500" />;
      case 1:
        return <Medal className="h-4 w-4 text-slate-300" />;
      case 2:
        return <Medal className="h-4 w-4 text-amber-600" />;
      default:
        return <span className="text-[10px] font-bold text-slate-500">{index + 1}</span>;
    }
  };

  return (
    <>
      <Card
        className={`mx-4 md:mx-0 col-span-full backdrop-blur-xl bg-opacity-60 dark:bg-black/60 border-white/20 shadow-xl rounded-2xl overflow-hidden group transition-all duration-500 ${isExpanded ? 'min-h-[500px]' : ''}`}
      >
        <CardHeader className="flex flex-row items-center justify-between px-8">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-500" />
            <CardTitle className="text-xl font-bold">Contributor Hall of Fame</CardTitle>
          </div>

          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 px-3 rounded-xl border-white/10 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all flex items-center gap-2 font-black uppercase text-[10px] tracking-widest shadow-lg active:scale-95"
            >
              {isExpanded ? (
                <>
                  <Minimize2 className="h-3.5 w-3.5" />
                  Show Less
                </>
              ) : (
                <>
                  <Maximize2 className="h-3.5 w-3.5" />
                  View All
                </>
              )}
            </Button>

            {!isExpanded && (
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => scroll('left')}
                  disabled={!canScrollLeft}
                  className={`h-8 w-8 rounded-full border border-white/10 hover:bg-white/5 transition-all text-slate-400 hover:text-white ${!canScrollLeft ? 'opacity-20 grayscale' : 'opacity-100'}`}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => scroll('right')}
                  disabled={!canScrollRight}
                  className={`h-8 w-8 rounded-full border border-white/10 hover:bg-white/5 transition-all text-slate-400 hover:text-white ${!canScrollRight ? 'opacity-20 grayscale' : 'opacity-100'}`}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="relative px-8 pb-8 pt-0">
          <motion.div
            layout
            ref={scrollRef}
            className={`flex gap-8 ${
              isExpanded
                ? 'flex-wrap justify-center overflow-y-auto max-h-[600px]'
                : 'overflow-x-auto scrollbar-hide snap-x items-start pb-4'
            }`}
            style={{
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
            }}
            transition={{
              layout: { duration: 0.5, type: 'spring', stiffness: 200, damping: 25 },
            }}
          >
            <LayoutGroup>
              {contributors.map((contributor, index) => (
                <motion.div
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{
                    delay: isExpanded ? 0 : (index % 5) * 0.05,
                    layout: { duration: 0.4, type: 'spring', stiffness: 200, damping: 25 },
                  }}
                  key={contributor.login}
                  onClick={() => setSelectedContributor(contributor)}
                  className="flex-shrink-0 w-[200px] flex flex-col items-center p-6 rounded-2xl bg-slate-50 dark:bg-white/5 border border-white/5 hover:border-blue-500/30 transition-shadow group/item relative snap-start cursor-pointer active:scale-95 shadow-md"
                >
                  <div className="absolute top-2 right-4">{getRankIcon(index)}</div>

                  <Avatar className="h-16 w-16 ring-4 ring-offset-4 ring-offset-slate-950 ring-transparent group-hover/item:ring-blue-500/50 transition-all duration-500">
                    <AvatarImage src={contributor.avatar_url} alt={contributor.login} />
                    <AvatarFallback>{contributor.login[0]}</AvatarFallback>
                  </Avatar>

                  {/* Hover Insight Hint */}
                  <div className="absolute top-12 left-1/2 -translate-x-1/2 opacity-0 group-hover/item:opacity-100 transition-opacity bg-blue-600 text-white text-[8px] font-black uppercase px-2 py-1 rounded shadow-lg pointer-events-none flex items-center gap-1 z-20">
                    <BarChart2 className="h-2 w-2" />
                    View Insights
                  </div>

                  <div className="mt-4 text-center w-full flex flex-col items-center gap-1">
                    <p className="text-sm font-black tracking-tight leading-none mb-1 capitalize truncate max-w-full">
                      {contributor.login}
                    </p>
                    <div className="flex flex-col items-center gap-1">
                      <a
                        href={contributor.html_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-[10px] uppercase font-black text-slate-400 hover:text-white tracking-widest transition-colors flex items-center gap-1 border-b border-transparent hover:border-white/20"
                      >
                        GitHub Profile
                      </a>
                    </div>
                  </div>

                  <div className="mt-4 px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-[10px] font-black uppercase tracking-tighter">
                    {contributor.contributions} Commits
                  </div>
                </motion.div>
              ))}
            </LayoutGroup>
            {/* Spacing element at the end */}
            {!isExpanded && <div className="flex-shrink-0 w-4" />}
          </motion.div>
        </CardContent>
      </Card>

      <ContributorDetailsModal
        contributor={selectedContributor}
        isOpen={!!selectedContributor}
        onClose={() => setSelectedContributor(null)}
      />
    </>
  );
}
