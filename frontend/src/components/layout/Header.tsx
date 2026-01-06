import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Database, LogOut, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { NavLink } from '@/components/NavLink';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

export function Header() {
  const { t } = useTranslation();
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-card shadow-sm">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 transition-opacity hover:opacity-80">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold">Tax Legal RAG</span>
          </Link>
          
          <nav className="hidden md:flex items-center gap-1">
            <NavLink
              to="/documents"
              className="px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground rounded-md"
              activeClassName="bg-muted text-foreground"
            >
              {t('nav.documents')}
            </NavLink>
            <NavLink
              to="/graph"
              className="px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground rounded-md"
              activeClassName="bg-muted text-foreground"
            >
              {t('nav.graph')}
            </NavLink>
            <NavLink
              to="/qa"
              className="px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground rounded-md"
              activeClassName="bg-muted text-foreground"
            >
              {t('nav.qa')}
            </NavLink>
            <NavLink
              to="/annotate"
              className="px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground rounded-md"
              activeClassName="bg-muted text-foreground"
            >
              {t('nav.annotate')}
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          {isAuthenticated && user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      {user.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{user.name}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/annotate" className="flex items-center cursor-pointer">
                    <User className="mr-2 h-4 w-4" />
                    {t('nav.dashboard')}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="cursor-pointer text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('nav.logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild variant="default">
              <Link to="/login">{t('nav.login')}</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
