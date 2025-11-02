'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { 
  Sparkles, 
  MessageSquare, 
  Plus,
  ChevronRight,
  Wallet,
  Copy,
  ExternalLink,
  Loader2,
  User,
  LogOut
} from "lucide-react";
import { usePathname, useRouter } from 'next/navigation';
import { apiClient, isAuthenticated } from "@/lib/api-client";
import type { AuthResponse } from "@/lib/api-client";
import { toast } from "sonner";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [walletAddress] = useState('0x742d...92a8');
  const [walletBalance] = useState('9.99');
  const [userProfile, setUserProfile] = useState<AuthResponse | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [isAuthChecking, setIsAuthChecking] = useState(true);
  
  const pathname = usePathname();

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = () => {
      if (!isAuthenticated()) {
        toast.error('Please login to access dashboard');
        router.push('/');
        return false;
      }
      setIsAuthChecking(false);
      return true;
    };

    if (!checkAuth()) {
      return;
    }
  }, [router]);

  // Initialize user profile on mount
  useEffect(() => {
    if (isAuthChecking) return;

    const initData = async () => {
      try {
        // Fetch user profile
        setProfileLoading(true);
        const profile = await apiClient.users.getProfile();
        setUserProfile(profile);
        // Update localStorage with fresh user data
        if (typeof window !== 'undefined') {
          localStorage.setItem('user', JSON.stringify(profile));
        }
        setProfileLoading(false);
        
        toast.success('Welcome back!', {
          description: 'Your dashboard is ready',
        });
      } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        setProfileLoading(false);
        
        // If profile fetch fails, user might not be authenticated
        if (error instanceof Error && error.message.includes('401')) {
          toast.error('Session expired, please login again');
          router.push('/');
          return;
        }
        
        toast.error('Failed to load dashboard data', {
          description: error instanceof Error ? error.message : 'Please try refreshing the page',
        });
      }
    };

    initData();
  }, [isAuthChecking, router]);

  const getBreadcrumb = () => {
    const path = pathname.split('/').filter(Boolean);
    if (path.length === 1) return 'Chat';
    return path[path.length - 1].charAt(0).toUpperCase() + path[path.length - 1].slice(1);
  };

  // Show loading state while checking authentication
  if (isAuthChecking) {
    return (
      <div className="flex h-screen w-full bg-[#0F172A] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-[#F7931A] animate-spin" />
          <p className="text-white/60">Checking authentication...</p>
        </div>
      </div>
    );
  }

  

  const recentChats = [
    { 
      id: 1, 
      title: 'Deploy smart contract', 
      preview: 'Create a liquidity pool smart contract and deploy it to Mezo testnet',
    },
    { 
      id: 2, 
      title: 'Explain Mezo architecture', 
      preview: 'How does the Bitcoin L2 layer work with Mezo protocol?',
    },
    { 
      id: 3, 
      title: 'Gas optimization tips', 
      preview: 'Best practices for reducing gas costs in smart contracts',

    },
    { 
      id: 4, 
      title: 'Python data analysis', 
      preview: 'Run analysis on blockchain transaction data',
    },
  ];

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full bg-[#0F172A] text-white overflow-hidden">
        {/* Sidebar */}
        <Sidebar className="border-r border-white/10 bg-[#1e1b4b]" style={{ 
          '--sidebar-background': '#1e1b4b',
          '--sidebar-foreground': 'white',
          '--sidebar-primary': '#F7931A',
          '--sidebar-primary-foreground': 'white',
          '--sidebar-accent': 'rgba(255, 255, 255, 0.05)',
          '--sidebar-accent-foreground': 'white',
          '--sidebar-border': 'rgba(255, 255, 255, 0.1)',
        } as React.CSSProperties}>
          {/* Logo Section */}
          <SidebarHeader className="border-b border-white/10 bg-[#1e1b4b]">
            <div className="flex items-center gap-3 px-4 py-4">
              <div className="w-10 h-10 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-lg flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="text-lg font-bold text-white">JARVIS</div>
                <div className="text-xs text-white/60">Your AI Agent</div>
              </div>
            </div>
          </SidebarHeader>

          <SidebarContent className="bg-[#1e1b4b]">
            {/* Recent Conversations */}
            <SidebarGroup className="bg-[#1e1b4b]">
              <SidebarGroupLabel className="text-xs font-semibold text-white/60 px-4 bg-[#1e1b4b]">
                RECENT CHATS
              </SidebarGroupLabel>
              <SidebarGroupContent className="bg-[#1e1b4b]">
                <SidebarMenu className="bg-[#1e1b4b]">
                  {recentChats.map((chat) => {
                    return (
                      <SidebarMenuItem key={chat.id} className="bg-[#1e1b4b]">
                        <SidebarMenuButton 
                          asChild 
                          className="text-white/60 hover:bg-white/5 hover:text-white bg-[#1e1b4b] h-auto py-2"
                          title={chat.preview}
                        >
                          <div className="flex items-start gap-2 cursor-pointer w-full">
                            <MessageSquare className="w-3.5 h-3.5 text-white/40 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2 mb-0.5">
                                <div className="text-xs text-white/80 truncate font-medium">
                                  {chat.title}
                                </div>
                              </div>
                              <div className="text-[10px] text-white/40 truncate mb-1">
                                {chat.preview}
                              </div>

                            </div>
                          </div>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          {/* Footer */}
          <SidebarFooter className="border-t border-white/10 bg-[#1e1b4b]">
            <div className="p-4">
              <Button 
                className="w-full bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-semibold"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Chat
              </Button>
            </div>
          </SidebarFooter>
        </Sidebar>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Navigation Bar */}
          <header className="h-16 border-b border-white/10 bg-[#1e1b4b]/50 backdrop-blur-sm flex items-center justify-between px-6">
            {/* Left: Sidebar Toggle & Breadcrumb */}
            <div className="flex items-center gap-4">
              <SidebarTrigger className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60" />
              <div className="flex items-center gap-2 text-sm">
                <span className="text-white/60">Dashboard</span>
                <ChevronRight className="w-4 h-4 text-white/40" />
                <span className="text-white font-medium">{getBreadcrumb()}</span>
              </div>
            </div>

          {/* Right: Notifications & User */}
          <div className="flex items-center gap-4">
            {/* Wallet Section */}
            <div className="flex items-center gap-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg px-4 py-2 hover:bg-white/10 transition-colors cursor-pointer group">
              <Wallet className="w-4 h-4 text-[#FCD34D]" />
              <div className="flex flex-col">
                <div className="text-[10px] text-white/40 uppercase tracking-wide">Balance</div>
                <div className="text-sm font-bold text-[#FCD34D]">{walletBalance} MEZO</div>
              </div>
              <div className="ml-2 pl-2 border-l border-white/20">
                <div className="text-xs text-white/60 font-mono flex items-center gap-1">
                  {walletAddress}
                  <button
                    onClick={() => navigator.clipboard.writeText('0x742d35a9f1234567890abcdef1234567890192a8')}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Copy full address"
                  >
                    <Copy className="w-3 h-3 text-white/40 hover:text-white" />
                  </button>
                  <button
                    onClick={() => window.open('https://explorer.mezo.io', '_blank')}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="View on explorer"
                  >
                    <ExternalLink className="w-3 h-3 text-white/40 hover:text-white" />
                  </button>
                </div>
              </div>
            </div>

            {/* User Profile Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 p-2 hover:bg-white/10 rounded-lg transition-colors">
                  <div className="w-8 h-8 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  {profileLoading ? (
                    <Loader2 className="w-4 h-4 text-white/40 animate-spin" />
                  ) : userProfile && (
                    <div className="text-left hidden md:block">
                      <div className="text-sm font-medium text-white">{userProfile.username}</div>
                      <div className="text-xs text-white/40">{userProfile.email}</div>
                    </div>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-[#1e1b4b] border-white/10">
                <DropdownMenuLabel className="text-white">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{userProfile?.username || 'User'}</p>
                    <p className="text-xs text-white/40">{userProfile?.email || ''}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem 
                  className="text-white/80 hover:bg-white/5 cursor-pointer"
                  onClick={() => router.push('/dashboard/profile')}
                >
                  <User className="w-4 h-4 mr-2" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem 
                  className="text-red-400 hover:bg-red-500/10 cursor-pointer"
                  onClick={async () => {
                    try {
                      // Wait for logout to complete
                      await apiClient.auth.logout();
                      
                      toast.success('Logged out successfully');
                      
                      // Navigate to landing page after logout completes
                      router.push('/');
                    } catch (error) {
                      console.error('Logout error:', error);
                      toast.error('Logout failed', {
                        description: 'Please try again',
                      });
                    }
                  }}
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        {children}
      </div>
      </div>
    </SidebarProvider>
  );
}
