"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  PlayCircle,
  Terminal,
  Settings,
  LayoutDashboard,
  Bug
} from 'lucide-react';

export default function Dashboard() {
  const [testRuns, setTestRuns] = useState<any[]>([]);
  const [activeRun, setActiveRun] = useState<any>(null);

  useEffect(() => {
    // Initial fetch
    fetchRuns();

    // Subscribe to realtime changes
    const subscription = supabase
      .channel('test_runs_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'test_runs' }, fetchRuns)
      .subscribe();

    return () => {
      supabase.removeChannel(subscription);
    };
  }, []);

  const fetchRuns = async () => {
    const { data } = await supabase
      .from('test_runs')
      .select('*, test_results(*, test_cases(name))')
      .order('started_at', { ascending: false })
      .limit(10);
      
    if (data && data.length > 0) {
      setTestRuns(data);
      setActiveRun(data[0]);
    }
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card p-4 flex flex-col">
        <div className="flex items-center gap-2 mb-8 px-2">
          <Bug className="w-6 h-6 text-accent" />
          <h1 className="font-bold text-lg tracking-tight">QA Agent</h1>
        </div>
        
        <nav className="flex-1 space-y-1">
          <Link href="/" className="flex items-center gap-3 px-3 py-2 bg-primary text-primary-foreground rounded-md">
            <LayoutDashboard className="w-4 h-4" />
            <span className="font-medium text-sm">Dashboard</span>
          </Link>
          <Link href="/runs" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors">
            <Activity className="w-4 h-4" />
            <span className="font-medium text-sm">Test Runs</span>
          </Link>
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors">
            <Settings className="w-4 h-4" />
            <span className="font-medium text-sm">Settings</span>
          </a>
        </nav>
        
        <div className="mt-auto">
          <button className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-green-600 text-white py-2 rounded-md transition-colors font-medium text-sm">
            <PlayCircle className="w-4 h-4" />
            Run All Tests
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-end">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-foreground">Real-time Monitor</h2>
            <p className="text-muted-foreground mt-1 text-sm">Watch the autonomous QA agent in action.</p>
          </div>
          {activeRun && activeRun.status === 'running' && (
            <div className="flex items-center gap-2 text-accent text-sm font-medium">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-accent"></span>
              </span>
              Agent is active
            </div>
          )}
        </header>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card border border-border p-5 rounded-xl">
            <div className="flex items-center gap-3 text-muted-foreground mb-2">
              <Activity className="w-4 h-4" />
              <h3 className="font-medium text-sm">Total Tests</h3>
            </div>
            <div className="text-3xl font-bold font-mono">{activeRun?.total_tests || 0}</div>
          </div>
          <div className="bg-card border border-border p-5 rounded-xl">
            <div className="flex items-center gap-3 text-pass mb-2">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="font-medium text-sm text-muted-foreground">Passed</h3>
            </div>
            <div className="text-3xl font-bold font-mono text-pass">{activeRun?.passed || 0}</div>
          </div>
          <div className="bg-card border border-border p-5 rounded-xl">
            <div className="flex items-center gap-3 text-fail mb-2">
              <XCircle className="w-4 h-4" />
              <h3 className="font-medium text-sm text-muted-foreground">Failed</h3>
            </div>
            <div className="text-3xl font-bold font-mono text-fail">{activeRun?.failed || 0}</div>
          </div>
          <div className="bg-card border border-border p-5 rounded-xl">
            <div className="flex items-center gap-3 text-info mb-2">
              <Clock className="w-4 h-4" />
              <h3 className="font-medium text-sm text-muted-foreground">Duration</h3>
            </div>
            <div className="text-3xl font-bold font-mono">{activeRun?.duration_seconds?.toFixed(1) || '0.0'}s</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Test Case List */}
          <div className="lg:col-span-2 bg-card border border-border rounded-xl flex flex-col">
            <div className="p-4 border-b border-border flex justify-between items-center">
              <h3 className="font-semibold">Recent Test Executions</h3>
            </div>
            <div className="p-0 overflow-y-auto max-h-[400px]">
              {activeRun?.test_results?.length ? (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground bg-muted/50 uppercase sticky top-0">
                    <tr>
                      <th className="px-6 py-3 font-medium">Status</th>
                      <th className="px-6 py-3 font-medium">Test Name</th>
                      <th className="px-6 py-3 font-medium">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {activeRun.test_results.map((res: any) => (
                      <tr key={res.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-6 py-4">
                          {res.status === 'pass' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-500 border border-green-500/20"><CheckCircle2 className="w-3 h-3"/> Pass</span>}
                          {res.status === 'fail' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-500 border border-red-500/20"><XCircle className="w-3 h-3"/> Fail</span>}
                          {res.status === 'error' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">Error</span>}
                        </td>
                        <td className="px-6 py-4 font-medium text-sm truncate max-w-[250px]">{res.test_cases?.name || res.test_case_id}</td>
                        <td className="px-6 py-4 font-mono text-xs">{res.duration_seconds}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <Terminal className="w-8 h-8 mb-2 opacity-50" />
                  <p className="text-sm">No results yet for this run</p>
                </div>
              )}
            </div>
          </div>

          {/* Live Log */}
          <div className="bg-black border border-border rounded-xl flex flex-col font-mono text-xs shadow-inner">
            <div className="p-3 border-b border-border/50 bg-[#111111] flex items-center gap-2 rounded-t-xl">
              <Terminal className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">agent.log</span>
            </div>
            <div className="p-4 overflow-y-auto max-h-[350px] space-y-2 text-[#A3B8CC]">
              {activeRun?.test_results?.[0]?.logs?.map((log: any, i: number) => (
                <div key={i} className="flex gap-3">
                  <span className="text-[#4D6680] shrink-0">{'>'}</span>
                  <span className="break-all">{typeof log === 'string' ? log : JSON.stringify(log)}</span>
                </div>
              ))}
              {(!activeRun?.test_results || activeRun.test_results.length === 0) && (
                <div className="text-[#4D6680] italic">Waiting for agent to start executing tests...</div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
