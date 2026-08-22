import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';
import Link from 'next/link';
import { useController } from 'react-hook-form';
import { Button } from '@/components/ui';
import { SocialLogin } from '@/components/auth';
import { StepProps } from '../registerTypes';

export default function TermsStep({
  methods,
  isLoading,
  onBack,
  lockoutTime = 0,
  handleFocus,
  canProceed,
}: StepProps & { lockoutTime?: number }) {
  const { field } = useController({
    control: methods.control,
    name: 'acceptTerms',
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4 text-primary">
        <Shield className="w-5 h-5" />
        <h3 className="font-semibold">Review & Submit</h3>
      </div>

      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm"
      >
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-muted-foreground">Name:</span>
            <p className="font-medium">
              {methods.getValues('firstName')} {methods.getValues('lastName')}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Username:</span>
            <p className="font-medium">{methods.getValues('username')}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Email:</span>
            <p className="font-medium">{methods.getValues('email')}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Age/Gender:</span>
            <p className="font-medium">
              {methods.getValues('age')} / {methods.getValues('gender')}
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex items-start space-x-3 p-3 bg-primary/5 rounded-lg border border-primary/10">
          <input
            type="checkbox"
            id="acceptTerms"
            checked={field.value || false}
            onChange={(e) => field.onChange(e.target.checked)}
            disabled={isLoading}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
            onFocus={() => handleFocus('acceptTerms')}
          />
          <label
            htmlFor="acceptTerms"
            className="text-sm text-muted-foreground cursor-pointer leading-tight"
          >
            I agree to the{' '}
            <Link
              href="/terms"
              className="text-primary hover:text-primary/80 underline"
              target="_blank"
            >
              Terms & Conditions
            </Link>
          </label>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex gap-3 pt-2"
      >
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={isLoading}
          className="flex-1"
        >
          <Shield className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button type="submit" disabled={isLoading || !field.value} className="flex-1">
          {isLoading && lockoutTime > 0 ? (
            `Retry in ${lockoutTime}s`
          ) : isLoading ? (
            <>
              <Shield className="mr-2 h-4 w-4" />
              Creating Account...
            </>
          ) : (
            <>
              <Shield className="mr-2 h-4 w-4" />
              Create Account
            </>
          )}
        </Button>
      </motion.div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
        <SocialLogin isLoading={isLoading} />
      </motion.div>
    </div>
  );
}