import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  AreaChart, Area 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, RefreshCw, Layers, DollarSign, Package, ShoppingBag, 
  Sparkles, ShieldAlert, ArrowUpRight, Search, BarChart3, Database
} from 'lucide-react';

const BRANDS = [
  "HK Vitals", "Kapiva", "MuscleBlaze", "Plix", "OZiva", 
  "Wellbeing Nutrition", "Fast&Up", "The Whole Truth", "Cosmix", "Setu Nutrition"
];

// Fallback frontend data generator to guarantee the dashboard works immediately with premium mock data
const generateFallbackData = (brand) => {
  const seedRandom = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return () => {
      const x = Math.sin(hash++) * 10000;
      return x - Math.floor(x);
    };
  };

  const rand = seedRandom(brand);
  const getRandRange = (min, max) => Math.floor(rand() * (max - min + 1)) + min;

  // Generate 3 products with 1-2 variants
  const products = [
    { name: "Daily Wellness Capsules", price: getRandRange(399, 699), variant: "60 Caps" },
    { name: "Premium Herbal Juice", price: getRandRange(299, 499), variant: "1 Litre" },
    { name: "Raw Plant Protein", price: getRandRange(1499, 2199), variant: "500g Pack" },
    { name: "Effervescent Energy Tablets", price: getRandRange(350, 590), variant: "20 Tabs" },
  ];

  // Last 7 days
  const chartData = [];
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  
  // Track current stock for each product variant to simulate daily changes
  const stockTracker = products.map(() => getRandRange(200, 600));

  days.forEach((day, index) => {
    const dataPoint = { date: day };
    products.forEach((p, idx) => {
      // simulate sales
      const sales = getRandRange(5, 45);
      dataPoint[`${p.name} (${p.variant})`] = sales;
      stockTracker[idx] = Math.max(10, stockTracker[idx] - sales);
      // restock
      if (stockTracker[idx] < 50) {
        stockTracker[idx] += getRandRange(300, 500);
      }
    });
    chartData.push(dataPoint);
  });

  // Generate table rows for today (Sunday / last day)
  const todayData = chartData[chartData.length - 1];
  const yesterdayData = chartData[chartData.length - 2];

  const tableData = products.map((p, idx) => {
    const key = `${p.name} (${p.variant})`;
    const soldToday = todayData[key];
    const soldYesterday = yesterdayData[key];
    
    // Starting stock = current stock + sold today
    const currentStock = stockTracker[idx];
    const startingStock = currentStock + soldToday;
    
    let dodChange = 0;
    if (soldYesterday > 0) {
      dodChange = parseFloat((((soldToday - soldYesterday) / soldYesterday) * 100).toFixed(1));
    }

    return {
      product_name: p.name,
      variant_title: p.variant,
      starting_stock: startingStock,
      current_stock: currentStock,
      units_sold_today: soldToday,
      dod_pct_change: dodChange,
      price: p.price
    };
  });

  // Calculate metrics
  let totalSoldToday = 0;
  let estRevenue = 0;
  let heroProduct = "";
  let maxSold = -1;

  tableData.forEach(row => {
    totalSoldToday += row.units_sold_today;
    estRevenue += row.units_sold_today * row.price;
    if (row.units_sold_today > maxSold) {
      maxSold = row.units_sold_today;
      heroProduct = `${row.product_name} (${row.variant_title})`;
    }
  });

  return {
    metrics: {
      total_sold_today: totalSoldToday,
      hero_product: heroProduct,
      est_revenue_today: estRevenue
    },
    table_data: tableData,
    chart_data: chartData
  };
};

function App() {
  const [selectedBrand, setSelectedBrand] = useState(BRANDS[0]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState('loading'); // 'api' or 'fallback'
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = async (brand) => {
    setLoading(true);
    try {
      // Use Vite env variable or default to local FastAPI port
      const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiBase}/api/dashboard?brand=${encodeURIComponent(brand)}`);
      if (!res.ok) throw new Error("API server responded with error");
      const apiData = await res.json();
      
      if (apiData.error) {
        throw new Error(apiData.error);
      }
      
      setData(apiData);
      setDataSource('api');
    } catch (err) {
      console.warn("Backend API not reachable. Falling back to local generation. Details:", err.message);
      // Fallback local mockup generator
      const mock = generateFallbackData(brand);
      setData(mock);
      setDataSource('fallback');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedBrand);
  }, [selectedBrand]);

  const handleRefresh = () => {
    fetchData(selectedBrand);
  };

  // Get keys of products in chart data
  const getProductKeys = () => {
    if (!data || !data.chart_data || data.chart_data.length === 0) return [];
    return Object.keys(data.chart_data[0]).filter(key => key !== 'date');
  };

  const productKeys = getProductKeys();

  // Colors for multi-line charts
  const LINE_COLORS = ["#d97706", "#10b981", "#ef4444", "#3b82f6", "#8b5cf6"];

  // Filter table data by search query
  const filteredTableData = data?.table_data.filter(row => 
    row.product_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    row.variant_title.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="min-h-screen flex bg-dark-900 text-zinc-100 selection:bg-gold-500/20 selection:text-amber-200">
      
      {/* SIDEBAR */}
      <aside className="w-80 border-r border-zinc-800/80 bg-zinc-950/60 backdrop-blur-xl flex flex-col z-10 shrink-0">
        
        {/* Brand/Logo Header */}
        <div className="p-6 border-b border-zinc-800/80 flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-tr from-amber-600 to-yellow-500 flex items-center justify-center shadow-lg shadow-amber-500/10">
            <BarChart3 className="h-5 w-5 text-zinc-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-amber-400 to-yellow-200 bg-clip-text text-transparent">
              VANTAGE D2C
            </h1>
            <p className="text-[10px] font-medium tracking-widest text-zinc-500 uppercase">
              Competitive Intelligence
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div className="px-6 py-4 border-b border-zinc-800/40 bg-zinc-900/10">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
            <span className="font-semibold flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5 text-amber-500" />
              Source Mode
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wide uppercase ${
              dataSource === 'api' 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {dataSource === 'api' ? 'SQLite Engine' : 'Sandboxed Mock'}
            </span>
          </div>
          {dataSource === 'fallback' && (
            <p className="text-[10px] leading-relaxed text-zinc-500">
              FastAPI is offline. Viewing auto-synthesized sandbox tracking metrics.
            </p>
          )}
        </div>

        {/* Sidebar Navigation (Brand Filter) */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1.5">
          <h2 className="px-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">
            Target Competitors ({BRANDS.length})
          </h2>
          {BRANDS.map((brand) => {
            const isActive = selectedBrand === brand;
            return (
              <button
                key={brand}
                onClick={() => setSelectedBrand(brand)}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-between group ${
                  isActive 
                    ? 'bg-amber-600/10 border border-amber-500/30 text-amber-300 shadow-sm shadow-amber-500/5' 
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/40 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={`h-1.5 w-1.5 rounded-full transition-all duration-300 ${
                    isActive ? 'bg-amber-400 scale-125' : 'bg-zinc-700 group-hover:bg-zinc-400'
                  }`} />
                  {brand}
                </div>
                {isActive && (
                  <ArrowUpRight className="h-4 w-4 text-amber-400/80" />
                )}
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-zinc-800/60 bg-zinc-950/40">
          <div className="text-[11px] text-zinc-500 flex flex-col gap-1">
            <span className="font-semibold text-zinc-400">Shopify Cart Reservation API</span>
            <span>Refreshes daily at 23:59 IST</span>
          </div>
        </div>
      </aside>

      {/* MAIN CONTAINER */}
      <main className="flex-1 overflow-y-auto p-10 space-y-8 max-w-7xl mx-auto w-full">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800/50 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 text-[9px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full tracking-widest uppercase">
                Active Audit
              </span>
              <span className="text-zinc-500 text-xs">•</span>
              <span className="text-xs text-zinc-400 font-medium">Daily Sales Velocities</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              {selectedBrand} <span className="font-light text-zinc-400">Storefront Metrics</span>
            </h1>
          </div>
          
          <div className="flex items-center gap-3 self-end sm:self-center">
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
              title="Sync Storefront Data"
            >
              <RefreshCw className={`h-4.5 w-4.5 ${loading ? 'animate-spin text-amber-500' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
            </button>
            <div className="text-xs text-zinc-500 text-right hidden sm:block">
              <p>Last checked: <span className="text-zinc-300 font-semibold">{data?.last_checked || 'Today, 11:59 PM'}</span></p>
              <p className="text-[10px]">Shopify API Integration</p>
            </div>
          </div>
        </div>

        {/* LOADING INDICATOR OR DASHBOARD CONTENT */}
        {loading && !data ? (
          <div className="h-[60vh] flex flex-col items-center justify-center gap-3 text-zinc-400">
            <RefreshCw className="h-8 w-8 animate-spin text-amber-500" />
            <p className="text-sm font-medium tracking-wide">Syncing product storefront inventories...</p>
          </div>
        ) : (
          <>
            {/* METRICS CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Card 1: Total Items Sold Today */}
              <div className="glass glass-gold-hover p-6 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-[0.03] text-white group-hover:scale-110 transition-transform duration-500 pointer-events-none">
                  <ShoppingBag className="h-28 w-28" />
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <ShoppingBag className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-semibold tracking-wider text-zinc-400 uppercase">
                    Total Units Sold Today
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-extrabold tracking-tight text-white">
                    {data?.metrics.total_sold_today}
                  </span>
                  <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/10 flex items-center gap-0.5">
                    <TrendingUp className="h-3 w-3" /> Live
                  </span>
                </div>
                <p className="text-[11px] text-zinc-500 mt-2">
                  Aggregated storefront velocity across all active variants.
                </p>
              </div>

              {/* Card 2: Hero Product */}
              <div className="glass glass-gold-hover p-6 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-[0.03] text-white group-hover:scale-110 transition-transform duration-500 pointer-events-none">
                  <Sparkles className="h-28 w-28" />
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-semibold tracking-wider text-zinc-400 uppercase">
                    Hero Product (Highest Velocity)
                  </span>
                </div>
                <div className="h-10 flex items-center">
                  <span className="text-lg font-bold tracking-tight text-zinc-100 line-clamp-2">
                    {data?.metrics.hero_product}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-500 mt-2">
                  Variant driving the highest storefront transactional load.
                </p>
              </div>

              {/* Card 3: Estimated Daily Revenue */}
              <div className="glass glass-gold-hover p-6 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-[0.03] text-white group-hover:scale-110 transition-transform duration-500 pointer-events-none">
                  <DollarSign className="h-28 w-28" />
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                    <DollarSign className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-semibold tracking-wider text-zinc-400 uppercase">
                    Estimated Daily Revenue
                  </span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-xs font-semibold text-zinc-400">Rs.</span>
                  <span className="text-4xl font-extrabold tracking-tight text-white">
                    {data?.metrics.est_revenue_today.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-500 mt-2">
                  Sales velocity multiplied by variants' standard public retail price.
                </p>
              </div>

            </div>

            {/* CHART SECTION */}
            <div className="glass p-6 rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    Sales Velocity Trend
                  </h3>
                  <p className="text-xs text-zinc-400">
                    7-day timeline of daily transactions for the top 5 performing items
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                  <span className="text-[11px] font-medium text-zinc-400">Velocity (units/day)</span>
                </div>
              </div>

              <div className="h-[320px] w-full pt-4">
                {productKeys.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={data.chart_data}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.3} vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="#71717a" 
                        fontSize={11} 
                        tickLine={false} 
                        axisLine={false} 
                      />
                      <YAxis 
                        stroke="#71717a" 
                        fontSize={11} 
                        tickLine={false} 
                        axisLine={false} 
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#18181b', 
                          border: '1px solid #3f3f46',
                          borderRadius: '8px',
                          color: '#fff',
                          fontFamily: 'sans-serif',
                          fontSize: '12px'
                        }}
                        cursor={{ stroke: '#3f3f46', strokeWidth: 1 }}
                      />
                      <Legend 
                        iconType="circle"
                        iconSize={8}
                        wrapperStyle={{ fontSize: '11px', paddingTop: '15px' }}
                      />
                      {productKeys.slice(0, 5).map((key, i) => (
                        <Line
                          key={key}
                          type="monotone"
                          dataKey={key}
                          stroke={LINE_COLORS[i % LINE_COLORS.length]}
                          strokeWidth={2.5}
                          dot={{ r: 3, strokeWidth: 1.5 }}
                          activeDot={{ r: 5 }}
                          animationDuration={800}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-zinc-500 text-xs">
                    No historical series data found for this competitor.
                  </div>
                )}
              </div>
            </div>

            {/* TABLE SECTION */}
            <div className="glass rounded-xl overflow-hidden space-y-4 p-6">
              
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    Inventory Inventory & Sales Ledger
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Real-time stock status and day-over-day movement per variant
                  </p>
                </div>
                
                {/* Search Bar */}
                <div className="relative max-w-xs w-full">
                  <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-zinc-500" />
                  <input
                    type="text"
                    placeholder="Search variants..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2 pl-9 pr-4 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-amber-500/50 transition-colors"
                  />
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider">
                      <th className="py-4.5 px-4 font-semibold">Product Name</th>
                      <th className="py-4.5 px-4 font-semibold">Variant</th>
                      <th className="py-4.5 px-4 font-semibold text-right">Starting Stock</th>
                      <th className="py-4.5 px-4 font-semibold text-right">Current Stock</th>
                      <th className="py-4.5 px-4 font-semibold text-right">Units Sold Today</th>
                      <th className="py-4.5 px-4 font-semibold text-right">Day-over-Day</th>
                      <th className="py-4.5 px-4 font-semibold text-right">Price</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/40 text-xs">
                    {filteredTableData.length > 0 ? (
                      filteredTableData.map((row, idx) => {
                        const isUntracked = row.current_stock < 0;
                        return (
                          <tr 
                            key={idx} 
                            className="hover:bg-zinc-800/20 transition-colors duration-150 group"
                          >
                            <td className="py-4 px-4 font-medium text-zinc-200 group-hover:text-amber-400 transition-colors">
                              {row.product_name}
                            </td>
                            <td className="py-4 px-4 text-zinc-400 font-mono">
                              {row.variant_title}
                            </td>
                            <td className="py-4 px-4 text-right font-mono text-zinc-400">
                              {isUntracked ? '-' : row.starting_stock}
                            </td>
                            <td className="py-4 px-4 text-right font-mono font-medium">
                              {isUntracked ? (
                                <span className="text-zinc-500 italic text-[11px]">Unlimited</span>
                              ) : (
                                <span className={row.current_stock < 30 ? 'text-amber-500 font-semibold' : 'text-zinc-200'}>
                                  {row.current_stock}
                                </span>
                              )}
                            </td>
                            <td className="py-4 px-4 text-right font-mono font-bold text-zinc-100">
                              {row.units_sold_today}
                            </td>
                            <td className="py-4 px-4 text-right font-mono">
                              {row.dod_pct_change > 0 ? (
                                <span className="text-emerald-400 font-semibold inline-flex items-center gap-0.5">
                                  <TrendingUp className="h-3 w-3" /> +{row.dod_pct_change}%
                                </span>
                              ) : row.dod_pct_change < 0 ? (
                                <span className="text-rose-500 font-semibold inline-flex items-center gap-0.5">
                                  <TrendingDown className="h-3 w-3" /> {row.dod_pct_change}%
                                </span>
                              ) : (
                                <span className="text-zinc-500">0.0%</span>
                              )}
                            </td>
                            <td className="py-4 px-4 text-right font-mono text-zinc-300 font-medium">
                              Rs. {row.price.toLocaleString('en-IN')}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="7" className="py-8 text-center text-zinc-500 italic">
                          No matching variants found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
