"use client";

import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { Send, AlertTriangle, CheckCircle, Truck, Globe } from "lucide-react";

interface Message {
  role: "user" | "ai";
  content: string;
}

interface Supplier {
  name: string;
  country: string;
  category: string;
  risk_level: string;
  trend: string;
}

// Simple SVG Gauge Component
const RiskGauge = ({ score }: { score: number }) => {
  const radius = 56; // Increased radius
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  let color = "text-green-500";
  if (score > 30) color = "text-yellow-500";
  if (score > 70) color = "text-red-500";

  return (
    <div className="relative flex items-center justify-center w-40 h-40">
      {/* Background Circle */}
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke="currentColor"
          strokeWidth="12"
          fill="transparent"
          className="text-slate-800"
        />
        {/* Progress Circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke="currentColor"
          strokeWidth="12"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${color} transition-all duration-1000 ease-out`}
        />
      </svg>
      {/* Score Text */}
      <div className="absolute flex flex-col items-center justify-center">
        <span className={`text-5xl font-black tracking-tighter ${color} drop-shadow-2xl`}>{score}</span>
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Risk Score</span>
      </div>
      {/* Pulse Effect for High Risk */}
      {score > 70 && (
        <div className="absolute inset-0 rounded-full bg-red-500/10 animate-ping"></div>
      )}
    </div>
  );
};

interface MonitoredRegion {
  name: string;
  status: 'safe' | 'warning' | 'critical';
  scanning?: boolean;
  riskScore?: number;
  suppliers?: Supplier[];
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [riskScore, setRiskScore] = useState<number | null>(null);
  const [impactedSuppliers, setImpactedSuppliers] = useState<Supplier[]>([]);
  const [report, setReport] = useState("");
  const [monitoredRegions, setMonitoredRegions] = useState<MonitoredRegion[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scanAllRegions = async (regions: MonitoredRegion[]) => {
    for (const region of regions) {
      // Mark as scanning
      setMonitoredRegions(prev => prev.map(r => r.name === region.name ? { ...r, scanning: true } : r));
      
      try {
        // Call backend silently
        const res = await axios.post("http://localhost:8000/analyze_risk", {
          query: `Check supply chain risks for ${region.name} based on current data.`
        });
        
        const suppliers = res.data.impacted_suppliers || [];
        const regionScore = res.data.risk_score || 0;
        
        const hasHigh = suppliers.some((s: any) => s.risk_level === 'High');
        const hasMedium = suppliers.some((s: any) => s.risk_level === 'Medium');
        
        let status: 'safe' | 'warning' | 'critical' = 'safe';
        if (hasHigh) status = 'critical';
        else if (hasMedium) status = 'warning';
        else if (regionScore > 50) status = 'warning'; // Fallback based on score
        
        // Update status and store data LOCALLY in the region object
        setMonitoredRegions(prev => prev.map(r => r.name === region.name ? { 
          ...r, 
          status, 
          scanning: false,
          riskScore: regionScore,
          suppliers: suppliers
        } : r));
        
      } catch (e) {
        console.error(`Error scanning ${region.name}:`, e);
        setMonitoredRegions(prev => prev.map(r => r.name === region.name ? { ...r, scanning: false } : r));
      }
    }
  };

  // Fetch monitored regions on mount and start scanning
  useEffect(() => {
    const fetchRegions = async () => {
      try {
        const res = await axios.get("http://localhost:8000/regions");
        const regions = (res.data.regions || []).map((r: string) => ({
          name: r,
          status: 'safe',
          scanning: false
        }));
        setMonitoredRegions(regions);
        
        // Start automatic scanning
        if (regions.length > 0) {
          scanAllRegions(regions);
        }
      } catch (error) {
        console.error("Error fetching regions:", error);
        setMonitoredRegions([
          { name: "Taiwan", status: 'safe' },
          { name: "Japan", status: 'safe' },
          { name: "Ukraine", status: 'safe' },
          { name: "USA", status: 'safe' }
        ]);
      }
    };
    fetchRegions();
  }, []);

  const handleAnalyze = async () => {
    if (!query.trim()) return;

    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setQuery("");

    try {
      const res = await axios.post("http://localhost:8000/analyze_risk", {
        query: userMsg.content,
      });

      const reportContent = res.data.report || "Analysis complete. No specific report generated.";
      const aiMsg: Message = { role: "ai", content: reportContent };
      
      setMessages((prev) => [...prev, aiMsg]);
      setRiskScore(res.data.risk_score);
      
      const newSuppliers: Supplier[] = res.data.impacted_suppliers || [];
      setImpactedSuppliers(newSuppliers); // Note: This replaces the list for specific queries
      setReport(res.data.report);

      // Update region status based on new findings
      if (newSuppliers.length > 0) {
        setMonitoredRegions(prev => prev.map(region => {
          const regionSuppliers = newSuppliers.filter(s => s.country === region.name);
          if (regionSuppliers.length === 0) return region;

          const hasHighRisk = regionSuppliers.some(s => s.risk_level === 'High');
          const hasMediumRisk = regionSuppliers.some(s => s.risk_level === 'Medium');

          let newStatus: 'safe' | 'warning' | 'critical' = region.status;
          if (hasHighRisk) newStatus = 'critical';
          else if (hasMediumRisk && region.status !== 'critical') newStatus = 'warning';
          
          return { ...region, status: newStatus };
        }));
      }

    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Error analyzing risk. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-screen bg-slate-950 text-white overflow-hidden font-sans selection:bg-blue-500/30">
      {/* Left Panel: Chat Interface */}
      <div className="w-1/2 flex flex-col border-r border-slate-800 bg-slate-900/50 backdrop-blur-sm">
        <div className="p-6 border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10">
          <h1 className="text-2xl font-bold flex items-center gap-3 tracking-tight">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Globe className="text-blue-400" size={24} />
            </div>
            <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
              Supply Chain Sentinel
            </span>
          </h1>
          <p className="text-slate-400 text-sm mt-1 ml-11">Agentic Risk Monitoring System</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-50">
              <Globe size={48} className="mb-4" />
              <p>Ready to monitor global supply chains.</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`p-4 rounded-2xl max-w-[85%] shadow-md ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-slate-800 border border-slate-700 text-slate-200 rounded-bl-none"
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-slate-400 ml-4">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-6 pb-8 bg-slate-900 border-t border-slate-800">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
              placeholder="Ask about supply chain risks..."
              className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-5 pr-12 py-4 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-inner"
            />
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg transition-all disabled:opacity-50 disabled:hover:bg-blue-600"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel: Control Room Dashboard */}
      <div className="w-1/2 p-8 bg-slate-950 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 bg-yellow-500/10 rounded-lg">
            <AlertTriangle className="text-yellow-500" size={24} />
          </div>
          <h2 className="text-xl font-bold text-white tracking-wide">Live Risk Dashboard</h2>
        </div>

        {/* Risk Score Section */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-8 backdrop-blur-md relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Global Risk Status</h3>
              <p className="text-2xl font-semibold text-white">
                {riskScore !== null ? (
                  riskScore > 70 ? "Critical Alert" : riskScore > 30 ? "Moderate Warning" : "Stable Operations"
                ) : "Waiting for Analysis..."}
              </p>
            </div>
            {riskScore !== null && <RiskGauge score={riskScore} />}
          </div>
        </div>

        {/* Impacted Suppliers Grid */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
              <Truck size={18} className="text-blue-400" />
              Impacted Suppliers
            </h3>
            {impactedSuppliers.length > 0 && (
              <span className="bg-slate-800 text-slate-400 text-xs px-2 py-1 rounded-full border border-slate-700">
                {impactedSuppliers.length} Detected
              </span>
            )}
          </div>

          {impactedSuppliers.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {impactedSuppliers.map((supplier, idx) => (
                <div
                  key={idx}
                  className="group relative bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 overflow-hidden"
                >
                  {/* Glass Gradient Overlay */}
                  <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
                  
                  {/* Top Row: Name & Risk Badge */}
                  <div className="flex justify-between items-start mb-4 relative z-10">
                    <h4 className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors">
                      {supplier.name}
                    </h4>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                      supplier.risk_level === 'High' ? 'bg-red-500/10 border-red-500/20 text-red-400 animate-pulse' :
                      supplier.risk_level === 'Medium' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                      'bg-green-500/10 border-green-500/20 text-green-400'
                    }`}>
                      {supplier.risk_level || 'Unknown'}
                    </span>
                  </div>

                  {/* Details Grid */}
                  <div className="space-y-3 relative z-10">
                    <div className="flex items-center gap-3 text-sm text-slate-400">
                      <Globe size={16} className="text-slate-500" />
                      <span>{supplier.country}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-slate-400">
                      <div className="w-4 h-4 rounded flex items-center justify-center bg-slate-800 text-[10px] font-bold text-slate-500">
                        C
                      </div>
                      <span>{supplier.category}</span>
                    </div>
                    {supplier.trend && (
                      <div className="flex items-center gap-3 text-sm">
                        <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                          supplier.trend.toLowerCase().includes('worsen') ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                        }`}>
                          <span className="text-[10px]">↗</span>
                        </div>
                        <span className={supplier.trend.toLowerCase().includes('worsen') ? 'text-red-400' : 'text-green-400'}>
                          {supplier.trend}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border border-dashed border-slate-800 rounded-xl p-8 flex flex-col items-center justify-center text-slate-500">
              <Truck size={32} className="mb-3 opacity-50" />
              <p>No specific suppliers flagged yet.</p>
            </div>
          )}
        </div>

        {/* Monitored Regions (Visual Anchors) */}
        <div className="mt-10 pt-8 border-t border-slate-800">
          <h3 className="text-lg font-semibold text-slate-200 mb-5 flex items-center gap-2">
            <Globe size={18} className="text-blue-400" />
            Monitored Regions
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {monitoredRegions.map((region) => (
              <div
                key={region.name}
                onClick={() => {
                  if (region.riskScore !== undefined) {
                    setRiskScore(region.riskScore);
                    setImpactedSuppliers(region.suppliers || []);
                  }
                }}
                className={`bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between hover:bg-slate-800 transition-all cursor-pointer hover:scale-[1.02] active:scale-95 ${
                  region.status === 'critical' ? 'border-red-500/30 bg-red-500/5' : 
                  region.status === 'warning' ? 'border-yellow-500/30 bg-yellow-500/5' : ''
                }`}
              >
                <div className="flex flex-col">
                  <div className="flex items-center gap-3 mb-1">
                    <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400">
                      {region.name.substring(0, 2).toUpperCase()}
                    </div>
                    <span className="text-slate-300 font-medium">{region.name}</span>
                  </div>
                  {region.riskScore !== undefined && region.riskScore > 0 && (
                    <span className={`text-xs font-bold ml-11 ${
                      region.riskScore > 70 ? 'text-red-400' : 
                      region.riskScore > 30 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      Score: {region.riskScore}
                    </span>
                  )}
                </div>
                
                <div className={`w-2 h-2 rounded-full shadow-[0_0_8px] ${
                  region.scanning ? 'bg-blue-400 animate-ping' :
                  region.status === 'critical' ? 'bg-red-500 shadow-red-500/50 animate-pulse' :
                  region.status === 'warning' ? 'bg-yellow-500 shadow-yellow-500/50' :
                  'bg-green-500 shadow-green-500/50'
                }`}></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
