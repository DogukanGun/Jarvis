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
  Bell, 
  Plus,
  ChevronRight,
  X,
  Wallet,
  Copy,
  ExternalLink,
  Play,
  Square,
  Loader2,
  User,
  Settings,
  LogOut
} from "lucide-react";
import { usePathname, useRouter } from 'next/navigation';
import { apiClient, saveContainerInfo } from "@/lib/api-client";
import type { Container, AuthResponse } from "@/lib/api-client";
import { toast } from "sonner";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [walletAddress] = useState('0x742d...92a8');
  const [walletBalance] = useState('9.99');
  const [container, setContainer] = useState<Container | null>(null);
  const [containerLoading, setContainerLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<AuthResponse | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, type: 'success', title: 'Agent Started', message: 'Your agent is now running', unread: true },
    { id: 2, type: 'info', title: 'New Feature', message: 'Voice input is now available', unread: true },
    { id: 3, type: 'warning', title: 'Low Balance', message: 'Your balance is running low', unread: false },
    { id: 4, type: 'success', title: 'Task Completed', message: 'Smart contract deployed successfully', unread: false },
  ]);
  
  const pathname = usePathname();
  
  const unreadCount = notifications.filter(n => n.unread).length;

  // Initialize container and user profile on mount
  useEffect(() => {
    const initData = async () => {
      try {
        // Fetch container status
        setContainerLoading(true);
        const status = await apiClient.containers.getStatus();
        setContainer(status);
        saveContainerInfo(status);
        setContainerLoading(false);
        
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
          description: `Agent is ${status.is_running ? 'running' : 'stopped'}`,
        });
      } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        setContainerLoading(false);
        setProfileLoading(false);
        toast.error('Failed to load dashboard data', {
          description: error instanceof Error ? error.message : 'Please try refreshing the page',
        });
      }
    };

    initData();
  }, []);

  const handleStartContainer = async () => {
    if (!container) return;
    try {
      setContainerLoading(true);
      await apiClient.containers.start();
      const status = await apiClient.containers.getStatus();
      setContainer(status);
      saveContainerInfo(status);
      toast.success('Agent started successfully', {
        description: 'Your agent is now ready to use',
      });
    } catch (error) {
      console.error('Failed to start container:', error);
      toast.error('Failed to start agent', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setContainerLoading(false);
    }
  };

  const handleStopContainer = async () => {
    if (!container) return;
    try {
      setContainerLoading(true);
      await apiClient.containers.stop();
      const status = await apiClient.containers.getStatus();
      setContainer(status);
      saveContainerInfo(status);
      toast.info('Agent stopped', {
        description: 'Your agent has been stopped',
      });
    } catch (error) {
      console.error('Failed to stop container:', error);
      toast.error('Failed to stop agent', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setContainerLoading(false);
    }
  };
  
  const markAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, unread: false } : n
    ));
  };
  
  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, unread: false })));
  };
  
  const removeNotification = (id: number) => {
    setNotifications(notifications.filter(n => n.id !== id));
  };

  const getBreadcrumb = () => {
    const path = pathname.split('/').filter(Boolean);
    if (path.length === 1) return 'Chat';
    return path[path.length - 1].charAt(0).toUpperCase() + path[path.length - 1].slice(1);
  };

  

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
            {/* Agent Status */}
            <SidebarGroup className="bg-[#1e1b4b]">
              <SidebarGroupLabel className="text-xs font-semibold text-white/60 px-4 bg-[#1e1b4b]">
                AGENT STATUS
              </SidebarGroupLabel>
              <SidebarGroupContent className="bg-[#1e1b4b] px-4 pb-3">
                <div className="bg-white/5 rounded-lg p-3 space-y-2">
                  {containerLoading ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 text-[#F7931A] animate-spin" />
                      <span className="text-sm text-white/60">Initializing...</span>
                    </div>
                  ) : container ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white/40">Status</span>
                        <div className="flex items-center gap-1.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${
                            container.is_running ? 'bg-green-400' : 'bg-red-400'
                          }`}></div>
                          <span className="text-xs font-medium text-white/80 capitalize">
                            {container.is_running ? 'Running' : 'Stopped'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white/40">Port</span>
                        <span className="text-xs font-mono text-white/60">{container.port}</span>
                      </div>
                      <div className="flex gap-2 pt-1">
                        {container.is_running ? (
                          <Button
                            onClick={handleStopContainer}
                            disabled={containerLoading}
                            size="sm"
                            variant="outline"
                            className="flex-1 h-7 text-xs bg-red-500/10 border-red-500/20 text-red-300 hover:bg-red-500/20"
                          >
                            <Square className="w-3 h-3 mr-1" />
                            Stop
                          </Button>
                        ) : (
                          <Button
                            onClick={handleStartContainer}
                            disabled={containerLoading}
                            size="sm"
                            className="flex-1 h-7 text-xs bg-green-500/10 border-green-500/20 text-green-300 hover:bg-green-500/20"
                          >
                            <Play className="w-3 h-3 mr-1" />
                            Start
                          </Button>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-white/40 text-center">No agent container</div>
                  )}
                </div>
              </SidebarGroupContent>
            </SidebarGroup>
           
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

            {/* Notifications Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="relative p-2 hover:bg-white/10 rounded-lg transition-colors">
                  <Bell className="w-5 h-5 text-white/60" />
                  {unreadCount > 0 && (
                    <div className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                      <span className="text-[10px] font-bold text-white">{unreadCount}</span>
                    </div>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80 bg-[#1e1b4b] border-white/10">
                <DropdownMenuLabel className="flex items-center justify-between">
                  <span className="text-white">Notifications</span>
                  {unreadCount > 0 && (
                    <button 
                      onClick={markAllAsRead}
                      className="text-xs text-[#F7931A] hover:text-[#FCD34D] transition-colors"
                    >
                      Mark all as read
                    </button>
                  )}
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-white/10" />
                
                {notifications.length === 0 ? (
                  <div className="px-2 py-8 text-center text-white/40 text-sm">
                    No notifications
                  </div>
                ) : (
                  <div className="max-h-[400px] overflow-y-auto">
                    {notifications.map((notification) => (
                      <DropdownMenuItem 
                        key={notification.id}
                        className="flex items-start gap-3 px-3 py-3 cursor-pointer focus:bg-white/5 hover:bg-white/5"
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className={`shrink-0 w-2 h-2 rounded-full mt-1.5 ${
                          notification.type === 'success' ? 'bg-green-500' :
                          notification.type === 'warning' ? 'bg-yellow-500' :
                          notification.type === 'error' ? 'bg-red-500' :
                          'bg-blue-500'
                        } ${notification.unread ? 'animate-pulse' : 'opacity-50'}`}></div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div className={`text-sm font-medium ${notification.unread ? 'text-white' : 'text-white/60'}`}>
                              {notification.title}
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeNotification(notification.id);
                              }}
                              className="shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
                            >
                              <X className="w-3 h-3 text-white/40 hover:text-white/80" />
                            </button>
                          </div>
                          <p className={`text-xs mt-1 ${notification.unread ? 'text-white/60' : 'text-white/40'}`}>
                            {notification.message}
                          </p>
                        </div>
                      </DropdownMenuItem>
                    ))}
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

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
                <DropdownMenuItem 
                  className="text-white/80 hover:bg-white/5 cursor-pointer"
                  onClick={() => router.push('/dashboard/settings')}
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem 
                  className="text-red-400 hover:bg-red-500/10 cursor-pointer"
                  onClick={() => {
                    apiClient.auth.logout();
                    toast.success('Logged out successfully');
                    router.push('/login');
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
