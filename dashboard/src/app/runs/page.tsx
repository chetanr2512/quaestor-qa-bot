"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import {
  Activity,
  CheckCircle2,
  XCircle,
  LayoutDashboard,
  Bug,
  Settings,
  PlayCircle,
  Download,
  ChevronDown,
  ChevronUp,
  Clock,
  Trash2,
  DollarSign
} from 'lucide-react';

export default function TestRunsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const PAGE_SIZE = 10;

  useEffect(() => {
    fetchRuns(currentPage);
  }, [currentPage]);

  const fetchRuns = async (page: number) => {
    setLoading(true);
    
    // Get total count for pagination
    const { count } = await supabase
      .from('test_runs')
      .select('*', { count: 'exact', head: true });
      
    if (count !== null) {
      setTotalPages(Math.ceil(count / PAGE_SIZE));
    }

    const from = (page - 1) * PAGE_SIZE;
    const to = from + PAGE_SIZE - 1;

    const { data } = await supabase
      .from('test_runs')
      .select('*, test_results(*, test_cases(name, type, priority, automation_status))')
      .order('started_at', { ascending: false })
      .range(from, to);
      
    if (data) setRuns(data);
    setLoading(false);
  };

  const downloadCSV = async () => {
    const { data: allResults } = await supabase
      .from('test_results')
      .select('*, test_cases(name, type, priority, automation_status)')
      .order('executed_at', { ascending: false });
      
    if (!allResults || allResults.length === 0) return;
    
    const headers = ["Test Result ID", "Test Case Name", "Type", "Status", "Duration (s)", "Error Message", "Executed At"];
    
    const rows = allResults.map(r => [
      r.id,
      r.test_cases?.name ? `"${r.test_cases.name.replace(/"/g, '""')}"` : "Unknown",
      r.test_cases?.type || "Unknown",
      r.status,
      r.duration_seconds,
      r.error_message ? `"${r.error_message.replace(/"/g, '""')}"` : "",
      new Date(r.executed_at).toLocaleString()
    ]);
    
    const csvContent = [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `qa_test_results_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleRun = (runId: string) => {
    setExpandedRunId(expandedRunId === runId ? null : runId);
  };

  const deleteRun = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this test run? This cannot be undone.')) return;
    
    // Optimistically update UI or just show loading state. 
    // We do a hard delete on results first in case cascade is not set up
    await supabase.from('test_results').delete().eq('test_run_id', runId);
    await supabase.from('test_runs').delete().eq('id', runId);
    
    fetchRuns(currentPage);
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
          <Link href="/" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors">
            <LayoutDashboard className="w-4 h-4" />
            <span className="font-medium text-sm">Dashboard</span>
          </Link>
          <Link href="/runs" className="flex items-center gap-3 px-3 py-2 bg-primary text-primary-foreground rounded-md">
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
            <h2 className="text-3xl font-bold tracking-tight text-foreground">Test Execution History</h2>
            <p className="text-muted-foreground mt-1 text-sm">View all historical test executions grouped by Test Run.</p>
          </div>
          <button 
            onClick={downloadCSV}
            className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Export Full CSV
          </button>
        </header>

        <div className="flex flex-col gap-4">
          {loading ? (
            <div className="p-12 text-center text-muted-foreground bg-card border border-border rounded-xl">Loading historical results...</div>
          ) : runs.length ? (
            <>
              {runs.map(run => (
                <div key={run.id} className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
                  <div 
                    className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors"
                    onClick={() => toggleRun(run.id)}
                  >
                    <div className="flex items-center gap-6">
                      <div className="flex flex-col">
                        <span className="text-sm text-muted-foreground font-medium">Started At</span>
                        <span className="font-semibold text-sm">{new Date(run.started_at).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-1.5"><Activity className="w-4 h-4 text-muted-foreground"/> <span>Total: {run.total_tests}</span></div>
                        <div className="flex items-center gap-1.5 text-pass"><CheckCircle2 className="w-4 h-4"/> <span>Passed: {run.passed}</span></div>
                        <div className="flex items-center gap-1.5 text-fail"><XCircle className="w-4 h-4"/> <span>Failed: {run.failed}</span></div>
                        <div className="flex items-center gap-1.5"><Clock className="w-4 h-4 text-muted-foreground"/> <span>{run.duration_seconds?.toFixed(1)}s</span></div>
                        <div className="flex items-center gap-1 text-green-600"><DollarSign className="w-4 h-4"/> <span className="font-medium">${(run.api_cost_usd || 0).toFixed(4)}</span></div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full uppercase tracking-wider ${run.status === 'completed' ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                        {run.status === 'running' && (Date.now() - new Date(run.started_at).getTime() > 30 * 60 * 1000) ? 'aborted' : run.status}
                      </span>
                      <button 
                        onClick={(e) => deleteRun(run.id, e)}
                        className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-md transition-colors"
                        title="Delete Run"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      {expandedRunId === run.id ? <ChevronUp className="w-5 h-5 text-muted-foreground" /> : <ChevronDown className="w-5 h-5 text-muted-foreground" />}
                    </div>
                  </div>
                  
                  {expandedRunId === run.id && (
                    <div className="border-t border-border bg-background">
                      {run.test_results && run.test_results.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm text-left whitespace-nowrap">
                            <thead className="text-xs text-muted-foreground bg-muted/50 uppercase border-b border-border">
                              <tr>
                                <th className="px-6 py-4 font-medium">Status</th>
                                <th className="px-6 py-4 font-medium">Test Name</th>
                                <th className="px-6 py-4 font-medium">Error Message</th>
                                <th className="px-6 py-4 font-medium">Type</th>
                                <th className="px-6 py-4 font-medium">Severity</th>
                                <th className="px-6 py-4 font-medium">Automation</th>
                                <th className="px-6 py-4 font-medium">Duration</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                              {run.test_results.map((res: any) => (
                                <tr key={res.id} className="hover:bg-muted/30 transition-colors">
                                  <td className="px-6 py-4">
                                    {res.status === 'pass' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-500 border border-green-500/20"><CheckCircle2 className="w-3 h-3"/> Pass</span>}
                                    {res.status === 'fail' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-500 border border-red-500/20"><XCircle className="w-3 h-3"/> Fail</span>}
                                    {res.status === 'error' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">Error</span>}
                                  </td>
                                  <td className="px-6 py-4 font-medium text-sm max-w-[250px] truncate" title={res.test_cases?.name || res.test_case_id}>
                                    {res.test_cases?.name || res.test_case_id}
                                  </td>
                                  <td className="px-6 py-4 font-mono text-xs max-w-[250px] truncate text-muted-foreground" title={res.error_message || 'N/A'}>
                                    {res.error_message || '-'}
                                  </td>
                                  <td className="px-6 py-4">
                                    <span className="px-2 py-1 bg-muted rounded-md text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                      {res.test_cases?.type || 'unknown'}
                                    </span>
                                  </td>
                                  <td className="px-6 py-4">
                                    <span className="px-2 py-1 bg-muted rounded-md text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                      {res.test_cases?.priority || 'unknown'}
                                    </span>
                                  </td>
                                  <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-md text-xs font-medium uppercase tracking-wider ${res.test_cases?.automation_status?.toLowerCase() === 'manual' ? 'bg-orange-500/10 text-orange-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                      {res.test_cases?.automation_status || 'unknown'}
                                    </span>
                                  </td>
                                  <td className="px-6 py-4 font-mono text-xs">{res.duration_seconds}s</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-6 text-center text-sm text-muted-foreground">No test results found for this run.</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              
              {/* Pagination Controls */}
              <div className="p-4 flex items-center justify-between bg-card border border-border rounded-xl mt-4">
                <div className="text-sm text-muted-foreground">
                  Showing page {currentPage} of {totalPages || 1}
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1.5 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  >
                    Previous
                  </button>
                  <button 
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    className="px-3 py-1.5 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-muted-foreground bg-card border border-border rounded-xl">No test runs found.</div>
          )}
        </div>
      </main>
    </div>
  );
}
