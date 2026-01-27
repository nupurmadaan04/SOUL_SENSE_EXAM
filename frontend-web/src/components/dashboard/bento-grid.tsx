import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

export const BentoGrid = ({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, staggerChildren: 0.1 }}
      className={cn(
        'grid md:auto-rows-[18rem] grid-cols-1 md:grid-cols-3 gap-6 max-w-7xl mx-auto ',
        className
      )}
    >
      {children}
    </motion.div>
  );
};

export const BentoGridItem = ({
  className,
  title,
  description,
  header,
  icon,
}: {
  className?: string;
  title?: string | React.ReactNode;
  description?: string | React.ReactNode;
  header?: React.ReactNode;
  icon?: React.ReactNode;
}) => {
  return (
    <motion.div
      whileHover={{ y: -5, transition: { duration: 0.2 } }}
      variants={{
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 },
      }}
      className={cn(
        'row-span-1 rounded-3xl group/bento hover:shadow-2xl transition duration-200 shadow-input dark:shadow-none p-6 dark:bg-black dark:border-white/[0.1] bg-white border border-transparent justify-between flex flex-col space-y-4',
        'backdrop-blur-xl bg-opacity-60 dark:bg-opacity-40 border-white/20 shadow-xl relative overflow-hidden', // Enhanced Glassmorphism
        className
      )}
    >
      {/* Background Glow Effect */}
      <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl blur opacity-0 group-hover:opacity-10 transition duration-500"></div>

      <div className="relative z-10 h-full flex flex-col justify-between">
        {header}
        <div className="group-hover/bento:translate-x-2 transition duration-200 mt-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">{icon}</div>
          </div>
          <div className="font-sans font-bold text-neutral-800 dark:text-neutral-100 text-lg mb-1">
            {title}
          </div>
          <div className="font-sans font-normal text-neutral-600 dark:text-neutral-400 text-sm leading-relaxed">
            {description}
          </div>
        </div>
      </div>
    </motion.div>
  );
};
