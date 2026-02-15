import React from "react";

type CategoryScore = {
  name: string;      // Name of the EQ category
  score: number;     // Percentage score (0-100)
  average?: number;  // Optional average value for comparison
};

interface CategoryBreakdownProps {
  categories: CategoryScore[]; // Array of all categories
  showLabels?: boolean;        // Show names and values
  animated?: boolean;          // Animate bars when rendered
}

const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({
  categories,
  showLabels = true,
  animated = true,
}) => {
  return (
    <div className="w-full space-y-4">
      {categories.map((category) => (
        <div key={category.name} className="w-full">
          {/* Category name and score label */}
          {showLabels && (
            <div className="flex justify-between text-sm font-medium mb-1">
              <span>{category.name}</span>
              <span>{category.score}%</span>
            </div>
          )}

          {/* Horizontal bar */}
          <div className="relative w-full h-5 bg-gray-200 rounded-full overflow-hidden">
            {/* Score bar */}
            <div
              className={`h-full bg-green-500 rounded-full ${
                animated ? "transition-all duration-700 ease-in-out" : ""
              }`}
              style={{ width: `${category.score}%` }}
            />

            {/* Optional average comparison line */}
            {category.average !== undefined && (
              <div
                className="absolute top-0 bottom-0 border-l-2 border-dashed border-black"
                style={{ left: `${category.average}%` }}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default CategoryBreakdown;
