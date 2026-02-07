'use client';

import React, { useMemo } from 'react';
import { Check, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { isWeakPassword } from '@/lib/validation/weak-passwords';

interface PasswordStrengthIndicatorProps {
    password: string;
}

interface Requirement {
    label: string;
    met: boolean;
}

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
    const isCommon = useMemo(() => password.length > 0 && isWeakPassword(password), [password]);

    const requirements: Requirement[] = useMemo(() => [
        { label: 'At least 8 characters', met: password.length >= 8 },
        { label: 'Contains uppercase letter', met: /[A-Z]/.test(password) },
        { label: 'Contains lowercase letter', met: /[a-z]/.test(password) },
        { label: 'Contains number', met: /[0-9]/.test(password) },
        { label: 'Contains special character', met: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
        { label: 'Not a commonly used password', met: !isCommon },
    ], [password, isCommon]);

    const strength = useMemo(() => {
        if (isCommon) return { level: 1, label: 'Weak - Common Password', color: 'bg-destructive' };
        const metCount = requirements.filter(r => r.met).length;
        if (metCount === 0) return { level: 0, label: '', color: 'bg-muted' };
        if (metCount <= 2) return { level: 1, label: 'Weak', color: 'bg-destructive' };
        if (metCount <= 3) return { level: 2, label: 'Fair', color: 'bg-warning' };
        if (metCount <= 4) return { level: 3, label: 'Good', color: 'bg-info' };
        if (metCount <= 5) return { level: 3, label: 'Good', color: 'bg-info' };
        return { level: 4, label: 'Strong', color: 'bg-success' };
    }, [requirements, isCommon]);

    if (!password) return null;

    return (
        <div className="space-y-3 mt-2">
            {/* Weak Password Warning Banner */}
            {isCommon && (
                <div className="flex items-center gap-2 bg-destructive/10 border border-destructive/20 text-destructive text-xs p-2.5 rounded-md">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                    <span className="font-medium">This password is too common. Please choose a stronger password.</span>
                </div>
            )}

            {/* Strength Bar */}
            <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                    <span className="text-xs text-muted-foreground">Password strength</span>
                    <span className={cn(
                        'text-xs font-medium',
                        strength.level === 1 && 'text-destructive',
                        strength.level === 2 && 'text-warning',
                        strength.level === 3 && 'text-info',
                        strength.level === 4 && 'text-success',
                    )}>
                        {strength.label}
                    </span>
                </div>
                <div className="flex gap-1">
                    {[1, 2, 3, 4].map((segment) => (
                        <div
                            key={segment}
                            className={cn(
                                'h-1.5 flex-1 rounded-full transition-all duration-300',
                                segment <= strength.level ? strength.color : 'bg-muted'
                            )}
                        />
                    ))}
                </div>
            </div>

            {/* Requirements Checklist */}
            <ul className="space-y-1">
                {requirements.map((req, index) => (
                    <li
                        key={index}
                        className={cn(
                            'flex items-center gap-2 text-xs transition-colors',
                            req.met ? 'text-success' : 'text-muted-foreground'
                        )}
                    >
                        {req.met ? (
                            <Check className="h-3 w-3" />
                        ) : (
                            <X className="h-3 w-3" />
                        )}
                        {req.label}
                    </li>
                ))}
            </ul>
        </div>
    );
}
