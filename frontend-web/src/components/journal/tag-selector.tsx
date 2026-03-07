'use client';

import React, { useState, KeyboardEvent } from 'react';
import { X, Plus, Tag as TagIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { PRESET_TAGS, EMOTION_CATEGORIES, EMOTION_EMOJIS, GENERAL_TAGS } from '@/types/journal';

interface TagSelectorProps {
    selected: string[];
    onChange: (tags: string[]) => void;
    presets?: string[] | readonly string[];
    allowCustom?: boolean;
    maxTags?: number;
    showEmojis?: boolean;
}

export function TagSelector({
    selected,
    onChange,
    presets = PRESET_TAGS,
    allowCustom = true,
    maxTags = 10,
    showEmojis = true,
}: TagSelectorProps) {
    const [inputValue, setInputValue] = useState('');
    const [isFocused, setIsFocused] = useState(false);

    const addTag = (tag: string) => {
        const trimmedTag = tag.trim();
        if (
            trimmedTag &&
            !selected.includes(trimmedTag) &&
            (maxTags === undefined || selected.length < maxTags)
        ) {
            onChange([...selected, trimmedTag]);
        }
        setInputValue('');
    };

    const removeTag = (tagToRemove: string) => {
        onChange(selected.filter((tag) => tag !== tagToRemove));
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && allowCustom) {
            e.preventDefault();
            addTag(inputValue);
        } else if (e.key === 'Backspace' && !inputValue && selected.length > 0) {
            removeTag(selected[selected.length - 1]);
        }
    };

    const getTagEmoji = (tag: string): string => {
        return EMOTION_EMOJIS[tag] || '🏷️';
    };

    const availablePresets = presets.filter((tag) => !selected.includes(tag));

    // Group tags by category (Issue #1334)
    const groupedTags = {
        emotions_positive: availablePresets.filter((tag) => 
            EMOTION_CATEGORIES.positive.includes(tag as any)
        ),
        emotions_negative: availablePresets.filter((tag) => 
            EMOTION_CATEGORIES.negative.includes(tag as any)
        ),
        emotions_neutral: availablePresets.filter((tag) => 
            EMOTION_CATEGORIES.neutral.includes(tag as any)
        ),
        general: availablePresets.filter((tag) => 
            GENERAL_TAGS.includes(tag as any)
        ),
        custom: availablePresets.filter((tag) => 
            !EMOTION_CATEGORIES.positive.includes(tag as any) &&
            !EMOTION_CATEGORIES.negative.includes(tag as any) &&
            !EMOTION_CATEGORIES.neutral.includes(tag as any) &&
            !GENERAL_TAGS.includes(tag as any)
        ),
    };

    return (
        <div className="space-y-4 w-full">
            {/* Selected Tags Display */}
            <div
                className={cn(
                    "min-h-[50px] p-2 rounded-xl border transition-all duration-200 bg-background/50 backdrop-blur-sm",
                    isFocused ? "border-primary ring-2 ring-primary/20 shadow-lg" : "border-border shadow-sm"
                )}
            >
                <div className="flex flex-wrap gap-2 items-center">
                    <AnimatePresence>
                        {selected.map((tag) => (
                            <motion.span
                                key={tag}
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary rounded-full text-sm font-medium border border-primary/20 hover:bg-primary/20 transition-colors"
                                layout
                            >
                                {showEmojis && <span className="text-base">{getTagEmoji(tag)}</span>}
                                {tag}
                                <button
                                    onClick={() => removeTag(tag)}
                                    className="hover:text-destructive transition-colors rounded-full hover:bg-destructive/10 p-0.5 ml-0.5"
                                    aria-label={`Remove ${tag}`}
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            </motion.span>
                        ))}
                    </AnimatePresence>

                    {allowCustom && (selected.length < (maxTags || Infinity)) && (
                        <div className="flex-1 min-w-[120px]">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                onFocus={() => setIsFocused(true)}
                                onBlur={() => setIsFocused(false)}
                                placeholder={selected.length === 0 ? "Add tags..." : ""}
                                className="w-full bg-transparent border-none outline-none text-sm placeholder:text-muted-foreground focus:ring-0 p-1"
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* Suggested Tags grouped by category (Issue #1334) */}
            <div className="space-y-3">
                {/* Positive Emotions */}
                {groupedTags.emotions_positive.length > 0 && (
                    <div>
                        <label className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wider flex items-center gap-1.5 px-1 mb-1.5">
                            <span className="text-lg">😊</span>
                            Positive Emotions
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {groupedTags.emotions_positive.map((tag) => (
                                <button
                                    key={tag}
                                    onClick={() => addTag(tag)}
                                    disabled={selected.length >= (maxTags || Infinity)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200 flex items-center gap-2",
                                        "bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30 hover:border-green-500/50 hover:bg-green-100/50 dark:hover:bg-green-500/20 hover:text-green-700 dark:hover:text-green-300",
                                        selected.length >= (maxTags || Infinity) && "opacity-50 cursor-not-allowed grayscale"
                                    )}
                                >
                                    {showEmojis && <span className="text-base">{getTagEmoji(tag)}</span>}
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Negative Emotions */}
                {groupedTags.emotions_negative.length > 0 && (
                    <div>
                        <label className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider flex items-center gap-1.5 px-1 mb-1.5">
                            <span className="text-lg">😢</span>
                            Challenging Emotions
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {groupedTags.emotions_negative.map((tag) => (
                                <button
                                    key={tag}
                                    onClick={() => addTag(tag)}
                                    disabled={selected.length >= (maxTags || Infinity)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200 flex items-center gap-2",
                                        "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 hover:border-red-500/50 hover:bg-red-100/50 dark:hover:bg-red-500/20 hover:text-red-700 dark:hover:text-red-300",
                                        selected.length >= (maxTags || Infinity) && "opacity-50 cursor-not-allowed grayscale"
                                    )}
                                >
                                    {showEmojis && <span className="text-base">{getTagEmoji(tag)}</span>}
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Neutral Emotions */}
                {groupedTags.emotions_neutral.length > 0 && (
                    <div>
                        <label className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider flex items-center gap-1.5 px-1 mb-1.5">
                            <span className="text-lg">😌</span>
                            Neutral Emotions
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {groupedTags.emotions_neutral.map((tag) => (
                                <button
                                    key={tag}
                                    onClick={() => addTag(tag)}
                                    disabled={selected.length >= (maxTags || Infinity)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200 flex items-center gap-2",
                                        "bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/30 hover:border-blue-500/50 hover:bg-blue-100/50 dark:hover:bg-blue-500/20 hover:text-blue-700 dark:hover:text-blue-300",
                                        selected.length >= (maxTags || Infinity) && "opacity-50 cursor-not-allowed grayscale"
                                    )}
                                >
                                    {showEmojis && <span className="text-base">{getTagEmoji(tag)}</span>}
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* General Tags */}
                {groupedTags.general.length > 0 && (
                    <div>
                        <label className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider flex items-center gap-1.5 px-1 mb-1.5">
                            <TagIcon className="w-4 h-4" />
                            Categories
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {groupedTags.general.map((tag) => (
                                <button
                                    key={tag}
                                    onClick={() => addTag(tag)}
                                    disabled={selected.length >= (maxTags || Infinity)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200 flex items-center gap-2",
                                        "bg-purple-50 dark:bg-purple-500/10 border-purple-200 dark:border-purple-500/30 hover:border-purple-500/50 hover:bg-purple-100/50 dark:hover:bg-purple-500/20 hover:text-purple-700 dark:hover:text-purple-300",
                                        selected.length >= (maxTags || Infinity) && "opacity-50 cursor-not-allowed grayscale"
                                    )}
                                >
                                    <Plus className="w-4 h-4" />
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Custom Tags */}
                {groupedTags.custom.length > 0 && (
                    <div>
                        <label className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5 px-1 mb-1.5">
                            <TagIcon className="w-4 h-4" />
                            More Tags
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {groupedTags.custom.map((tag) => (
                                <button
                                    key={tag}
                                    onClick={() => addTag(tag)}
                                    disabled={selected.length >= (maxTags || Infinity)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 flex items-center gap-1.5",
                                        "bg-secondary/50 border-border hover:border-primary/50 hover:bg-primary/5 hover:text-primary",
                                        selected.length >= (maxTags || Infinity) && "opacity-50 cursor-not-allowed grayscale"
                                    )}
                                >
                                    <Plus className="w-3 h-3" />
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* No more suggestions */}
                {availablePresets.length === 0 && (
                    <p className="text-xs text-muted-foreground italic px-1 py-2 text-center">
                        All tags selected
                    </p>
                )}
            </div>

            {/* Tag counter */}
            {maxTags && (
                <p className="text-[10px] text-muted-foreground text-right px-1">
                    {selected.length} / {maxTags} tags used
                </p>
            )}
        </div>
    );
}
