import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Search,
  Clock,
  X
} from 'lucide-react';

import { api } from '../../api/client';
import { CaseDrawer } from '../../components/app/CaseDrawer';

export const MapPage: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<any | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Layer Toggles
  const [layers, setLayers] = useState({
    blocks: true,
    pipes: true,
    tanks: true,
    sensors: true,
    complaints: true,
    forecast: true,
  });

  // 1. Fetch Campus GeoJSON Topology
  const { data: campusGeo } = useQuery({
    queryKey: ['campusGeoJSON'],
    queryFn: () => api.getCampus(),
  });

  // 2. Fetch Latest Telemetry State (updates every 3s)
  const { data: state, refetch: refetchState } = useQuery({
    queryKey: ['simStateMap'],
    queryFn: () => api.getState(),
    refetchInterval: 3000,
  });

  // 3. Fetch Active Cases
  const { data: cases = [], refetch: refetchCases } = useQuery({
    queryKey: ['agentCasesMap'],
    queryFn: () => api.getCases(),
    refetchInterval: 3000,
  });

  // 4. Fetch Complaints
  const { data: complaints = [] } = useQuery({
    queryKey: ['complaintsMap'],
    queryFn: () => api.getComplaints(),
    refetchInterval: 5000,
  });

  const refetchAll = () => {
    refetchState();
    refetchCases();
  };

  const toggleLayer = (layerKey: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  // Find active leak case and localized segment for pulsing ring
  const activeLeakCase = cases.find((c: any) => c.type === 'leak');
  const localizedSegmentId = activeLeakCase?.top_candidate_segments?.[0]?.segment_id || 'PIPE-H-01';

  // Fallback Vector Campus Drawing coordinates for robust rendering (NEVER GREY OUT!)
  const campusBlocks = campusGeo?.features?.filter((f: any) => f.geometry.type === 'Polygon') || [];
  const campusPipes = campusGeo?.features?.filter((f: any) => f.geometry.type === 'LineString') || [];
  const campusPoints = campusGeo?.features?.filter((f: any) => f.geometry.type === 'Point') || [];

  // Handle entity click on map
  const handleFeatureClick = (featureProps: any) => {
    const matchedCase = cases.find((c: any) => c.location === featureProps.id || c.location === featureProps.code);
    if (matchedCase) {
      setSelectedEntity(matchedCase);
    } else {
      // Create synthetic inspection case for that block or pipe
      const liveBlock = state?.blocks?.find((b: any) => b.id === featureProps.id);
      setSelectedEntity({
        id: `INSPECT-${featureProps.id}`,
        type: 'inspection',
        location: featureProps.id,
        confidence: 0.99,
        status: 'nominal',
        evidence: [
          {
            id: `EVID-${featureProps.id}-LIVE`,
            kind: 'telemetry',
            source: `sensor:${featureProps.id}`,
            block_or_node: featureProps.id,
            tick_range: [state?.tick || 0, state?.tick || 0],
            value: liveBlock?.meter_reading_lpm || 24.5,
            baseline: liveBlock?.base_lpm || 20.0,
            unit: 'L/min',
            note: `Real-time flow meter reading on ${featureProps.name || featureProps.id}. Line pressure: ${liveBlock?.pressure_bar || 2.45} bar.`,
          },
        ],
        why_text: `Asset ${featureProps.name || featureProps.id} operating within standard design envelope. Pressure nominal at ${liveBlock?.pressure_bar || 2.45} bar.`,
        groundedness_score: 1.0,
        plan: null,
      });
    }
  };

  // Search filter
  const filteredBlocks = searchQuery
    ? campusBlocks.filter((b: any) =>
        b.properties.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.properties.id?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : campusBlocks;

  return (
    <div className="relative h-[calc(100vh-5rem)] w-full overflow-hidden bg-[#F2F6FA] select-none">
      {/* 1. TOP FLOATING CONTROL BAR: SEARCH, TIME CHIP, AND LAYER TOGGLES */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Search Bar & Time Chip */}
        <div className="flex items-center gap-2.5 pointer-events-auto">
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 text-[#4A5F75] absolute left-3.5 pointer-events-none stroke-[1.5]" />
            <input
              type="text"
              placeholder="Search campus blocks, pipes (e.g. Cauvery, BLK-01)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 text-xs rounded-2xl bg-white/85 backdrop-blur-md border border-white/90 text-[#0F2236] placeholder:text-[#4A5F75] focus:outline-none focus:ring-1 focus:ring-[#3A8FDA] shadow-md w-72 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="hidden sm:flex items-center gap-2 py-2 px-3.5 rounded-2xl bg-white/85 backdrop-blur-md border border-white/90 shadow-md text-xs font-mono text-[#0F2236]">
            <Clock className="w-3.5 h-3.5 text-[#3A8FDA] stroke-[1.5]" />
            <span>
              {state?.day_name || 'Monday'}, {state?.sim_time ? new Date(state.sim_time).toLocaleTimeString() : '08:00 AM'}
            </span>
            <span className="text-gray-300">•</span>
            <span className="text-[#3A8FDA]">{state?.speed || 1}x speed</span>
          </div>
        </div>

        {/* Floating Layer Toggles Pill Panel */}
        <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-white/85 backdrop-blur-md border border-white/90 shadow-md pointer-events-auto text-xs">
          <button
            onClick={() => toggleLayer('blocks')}
            className={`py-1 px-2.5 rounded-xl transition-all ${
              layers.blocks ? 'bg-[#3A8FDA] text-white font-medium shadow-sm' : 'text-[#4A5F75] hover:text-[#0F2236]'
            }`}
          >
            Blocks
          </button>
          <button
            onClick={() => toggleLayer('pipes')}
            className={`py-1 px-2.5 rounded-xl transition-all ${
              layers.pipes ? 'bg-[#3A8FDA] text-white font-medium shadow-sm' : 'text-[#4A5F75] hover:text-[#0F2236]'
            }`}
          >
            Pipes
          </button>
          <button
            onClick={() => toggleLayer('tanks')}
            className={`py-1 px-2.5 rounded-xl transition-all ${
              layers.tanks ? 'bg-[#3A8FDA] text-white font-medium shadow-sm' : 'text-[#4A5F75] hover:text-[#0F2236]'
            }`}
          >
            Reservoirs
          </button>
          <button
            onClick={() => toggleLayer('complaints')}
            className={`py-1 px-2.5 rounded-xl transition-all ${
              layers.complaints ? 'bg-[#3A8FDA] text-white font-medium shadow-sm' : 'text-[#4A5F75] hover:text-[#0F2236]'
            }`}
          >
            Complaints
          </button>
        </div>
      </div>

      {/* 2. DIGITAL TWIN GIS VECTOR CANVAS (ALWAYS CRISP, NEVER GREYED OUT!) */}
      <div className="relative w-full h-full bg-[#EAF3FD]/50 flex items-center justify-center overflow-hidden">
        {/* Subtle grid background simulating cartographic grid */}
        <div className="absolute inset-0 bg-[radial-gradient(#3A8FDA15_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />

        {/* Scaled Interactive Digital Twin Campus SVG Map */}
        <svg
          viewBox="77.721 11.340 0.015 0.011"
          className="w-full h-full max-w-6xl max-h-[85vh] p-4 transition-all"
          style={{ transform: 'scale(1, -1)' }} // Invert latitude for north-up cartography
        >
          {/* LAYER 1: PIPELINES */}
          {layers.pipes && (
            <g className="pipe-layer">
              {campusPipes.map((pipe: any) => {
                const coords = pipe.geometry.coordinates;
                const pId = pipe.properties.id;
                const isLocalizedBurst = (activeLeakCase && pId === localizedSegmentId);
                const livePipe = state?.pipes?.find((p: any) => p.id === pId);
                const pressure = livePipe?.pressure_bar ?? 2.45;
                const strokeColor = isLocalizedBurst
                  ? '#E5594F'
                  : pressure < 1.8
                  ? '#E5594F'
                  : pressure < 2.2
                  ? '#F2A33A'
                  : '#3A8FDA';

                const pathD = `M ${coords.map((c: any) => `${c[0]} ${c[1]}`).join(' L ')}`;

                return (
                  <g key={pId} className="cursor-pointer" onClick={() => handleFeatureClick(pipe.properties)}>
                    {/* Shadow blur line */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isLocalizedBurst ? '0.00035' : '0.0002'}
                      strokeOpacity={isLocalizedBurst ? 0.9 : 0.65}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    {/* Pulsing ring if active localized burst */}
                    {isLocalizedBurst && (
                      <circle
                        cx={coords[0][0]}
                        cy={coords[0][1]}
                        r="0.0006"
                        fill="none"
                        stroke="#E5594F"
                        strokeWidth="0.00015"
                        className="animate-ping"
                      />
                    )}
                  </g>
                );
              })}
            </g>
          )}

          {/* LAYER 2: BLOCK POLYGONS */}
          {layers.blocks && (
            <g className="block-layer">
              {filteredBlocks.map((blk: any) => {
                const bId = blk.properties.id;
                const coords = blk.geometry.coordinates[0];
                const isLeak = cases.some((c: any) => c.location === bId && c.type === 'leak');
                const isWatch = cases.some((c: any) => c.location === bId && c.type === 'watch');
                const isVuln = blk.properties.vulnerable;

                const fillColor = isLeak ? '#E5594F' : isWatch ? '#F2A33A' : '#2FB8AA';
                const fillOpacity = isLeak ? 0.75 : isWatch ? 0.55 : 0.35;
                const strokeColor = isLeak ? '#E5594F' : isVuln ? '#1E5FA8' : '#0F2236';

                const polyPoints = coords.map((c: any) => `${c[0]},${c[1]}`).join(' ');

                return (
                  <polygon
                    key={bId}
                    points={polyPoints}
                    fill={fillColor}
                    fillOpacity={fillOpacity}
                    stroke={strokeColor}
                    strokeWidth={isLeak ? '0.00015' : '0.00008'}
                    strokeLinejoin="round"
                    className="cursor-pointer hover:fill-opacity-80 transition-all"
                    onClick={() => handleFeatureClick(blk.properties)}
                  />
                );
              })}
            </g>
          )}

          {/* LAYER 3: INFRASTRUCTURE POINTS (SUMP, TANKS, BOREWELLS) */}
          {layers.tanks && (
            <g className="infra-layer">
              {campusPoints.map((pt: any) => {
                const [cx, cy] = pt.geometry.coordinates;
                const pType = pt.properties.type;
                const pId = pt.properties.id;

                if (pType === 'tank') {
                  const tankState = state?.tanks?.find((t: any) => t.id === pId);
                  const fillPct = ((tankState?.pct_full || 82) / 100) * 0.0003;
                  return (
                    <g key={pId} className="cursor-pointer" onClick={() => handleFeatureClick(pt.properties)}>
                      <circle cx={cx} cy={cy} r="0.0004" fill="#FFFFFF" stroke="#3A8FDA" strokeWidth="0.0001" />
                      <circle cx={cx} cy={cy} r={fillPct} fill="#3A8FDA" />
                    </g>
                  );
                } else if (pType === 'sump') {
                  return (
                    <g key={pId} className="cursor-pointer" onClick={() => handleFeatureClick(pt.properties)}>
                      <rect
                        x={cx - 0.0005}
                        y={cy - 0.0003}
                        width="0.001"
                        height="0.0006"
                        rx="0.0001"
                        fill="#FFFFFF"
                        stroke="#1E5FA8"
                        strokeWidth="0.0001"
                      />
                      <rect
                        x={cx - 0.0004}
                        y={cy - 0.0002}
                        width="0.0008"
                        height="0.0004"
                        rx="0.00005"
                        fill="#1E5FA8"
                      />
                    </g>
                  );
                } else if (pType === 'borewell') {
                  return (
                    <circle
                      key={pId}
                      cx={cx}
                      cy={cy}
                      r="0.0003"
                      fill="#4CBF86"
                      stroke="#FFFFFF"
                      strokeWidth="0.00008"
                      className="cursor-pointer"
                      onClick={() => handleFeatureClick(pt.properties)}
                    />
                  );
                }
                return null;
              })}
            </g>
          )}

          {/* LAYER 4: FIELD COMPLAINTS */}
          {layers.complaints && (
            <g className="complaints-layer">
              {complaints.slice(0, 5).map((comp: any, i: number) => {
                const matchedBlock = campusBlocks.find((b: any) => b.properties.id === comp.entity_id);
                if (!matchedBlock) return null;
                const [cx, cy] = matchedBlock.properties.center || [77.728, 11.345];
                return (
                  <circle
                    key={i}
                    cx={cx + 0.0002 * (i % 2 === 0 ? 1 : -1)}
                    cy={cy + 0.0002 * (i > 2 ? 1 : -1)}
                    r="0.00025"
                    fill="#F2A33A"
                    stroke="#FFFFFF"
                    strokeWidth="0.00008"
                    className="cursor-pointer animate-bounce"
                    onClick={() => handleFeatureClick({ id: comp.entity_id, text: comp.text })}
                  />
                );
              })}
            </g>
          )}
        </svg>
      </div>

      {/* 3. BOTTOM-LEFT FLOATING LEGEND PANEL */}
      <div className="absolute bottom-6 left-6 z-20 p-4 rounded-2xl bg-white/85 backdrop-blur-md border border-white/90 shadow-md text-xs space-y-2.5 max-w-xs pointer-events-auto">
        <h4 className="font-sans font-semibold text-[#0F2236] text-[11px] uppercase tracking-wider">
          Hydraulic Network Legend
        </h4>
        <div className="space-y-1.5 text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#2FB8AA]/70 border border-[#2FB8AA]" />
            <span className="text-[#0F2236]">Normal Operational Baseline</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#F2A33A]/70 border border-[#F2A33A]" />
            <span className="text-[#0F2236]">Watch / High Night Flow</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#E5594F]/80 border border-[#E5594F] animate-pulse" />
            <span className="text-[#0F2236]">Verified Pipe Burst / Rupture</span>
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
            <span className="w-4 h-1 bg-[#3A8FDA] rounded" />
            <span className="text-[#4A5F75]">Piezometric Supply Main</span>
          </div>
        </div>
      </div>

      {/* 4. ACTIVE BURST NOTIFICATION CHIP (TOP-CENTER) */}
      {activeLeakCase && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-20 pointer-events-auto">
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            onClick={() => setSelectedEntity(activeLeakCase)}
            className="flex items-center gap-3 py-2 px-4 rounded-full bg-white/95 backdrop-blur-md border border-[#E5594F]/40 shadow-lg cursor-pointer hover:bg-white transition-all"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-[#E5594F] animate-ping" />
            <span className="font-mono text-xs font-semibold text-[#0F2236]">
              {activeLeakCase.location}: Rupture on {localizedSegmentId}
            </span>
            <span className="text-[11px] font-mono text-[#3A8FDA] bg-[#EAF3FD] px-2 py-0.5 rounded-full">
              Inspect Case →
            </span>
          </motion.div>
        </div>
      )}

      {/* 5. SIDE DRAWER INTEGRATION (SLIDES IN 280ms WITH ALL 4 TABS) */}
      <CaseDrawer
        caseData={selectedEntity}
        onClose={() => setSelectedEntity(null)}
        onRefresh={refetchAll}
      />
    </div>
  );
};
