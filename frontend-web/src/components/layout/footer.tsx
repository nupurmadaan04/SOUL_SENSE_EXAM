import Link from 'next/link';
import { BookOpen, Github, Twitter, Linkedin, Mail } from 'lucide-react';
import { Button } from '@/components/ui';

const footerLinks = {
  product: [
    { name: 'Features', href: '/#features' },
    { name: 'Testimonials', href: '/#testimonials' },
    { name: 'FAQ', href: '/faq' },
  ],
  company: [
    { name: 'About', href: '/#about' },
    { name: 'Contact Us', href: '/contact' },
    { name: 'Privacy Policy', href: '/privacy' },
    { name: 'Terms of Service', href: '/terms' },
  ],
  social: [
    { name: 'GitHub', href: 'https://github.com/nupurmadaan04', icon: Github },
    { name: 'LinkedIn', href: 'https://www.linkedin.com/in/nupurmadaan04', icon: Linkedin },
    { name: 'Twitter', href: 'https://twitter.com/nupurmadaan04', icon: Twitter },
    { name: 'Email', href: 'mailto:nupur.04.m@gmail.com', icon: Mail },
  ],
};

export function Footer() {
  return (
    <footer className="bg-background border-t">
      <div className="container mx-auto px-6 py-12 lg:px-8">
        <div className="xl:grid xl:grid-cols-3 xl:gap-8">
          <div className="space-y-8">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-md text-white">
                <BookOpen className="h-5 w-5" />
              </div>
              <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                Soul Sense
              </span>
            </Link>
            <p className="text-sm leading-6 text-muted-foreground max-w-xs">
              Empowering individuals through emotional intelligence. Discover your EQ and unlock
              your full potential with Soul Sense.
            </p>
            <div className="flex gap-x-6">
              {footerLinks.social.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  className="text-muted-foreground hover:text-primary transition-colors"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className="sr-only">{item.name}</span>
                  <item.icon className="h-6 w-6" aria-hidden="true" />
                </a>
              ))}
            </div>
          </div>
          <div className="mt-16 grid grid-cols-2 gap-8 xl:col-span-2 xl:mt-0">
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-foreground">Product</h3>
                <ul role="list" className="mt-6 space-y-4">
                  {footerLinks.product.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm leading-6 text-muted-foreground hover:text-primary transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold leading-6 text-foreground">Company</h3>
                <ul role="list" className="mt-6 space-y-4">
                  {footerLinks.company.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm leading-6 text-muted-foreground hover:text-primary transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="flex flex-col gap-4">
              <h3 className="text-sm font-semibold leading-6 text-foreground">Stay Updated</h3>
              <div className="flex flex-col gap-2">
                <p className="text-xs text-muted-foreground">
                  Subscribe to our newsletter for EQ tips and updates.
                </p>
                <div className="flex gap-2">
                  <input
                    type="email"
                    placeholder="Email address"
                    className="flex-1 min-w-0 rounded-md border bg-background px-3 py-1.5 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  />
                  <Button size="sm">Join</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-16 border-t pt-8 sm:mt-20 lg:mt-24 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs leading-5 text-muted-foreground">
            &copy; {new Date().getFullYear()} Soul Sense. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <Link href="/privacy" className="hover:text-primary transition-colors">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-primary transition-colors">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
