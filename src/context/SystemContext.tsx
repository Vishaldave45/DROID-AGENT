import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { systemApi, HealthResponse, SystemManifestResponse } from '../api';
import { SubsystemInfo } from '../types';
import { SUBSYSTEMS } from '../data/architectureData';

interface SystemContextType {
  health: HealthResponse | null;
  manifest: SystemManifestResponse | null;
  subsystems: SubsystemInfo[];
  demoMode: boolean;
  isLoading: boolean;
  refreshHealth: () => Promise<void>;
  refreshManifest: () => Promise<void>;
}

const SystemContext = createContext<SystemContextType | undefined>(undefined);

export const SystemProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [manifest, setManifest] = useState<SystemManifestResponse | null>(null);
  const [subsystems, setSubsystems] = useState<SubsystemInfo[]>(SUBSYSTEMS);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshHealth = async () => {
    try {
      const data = await systemApi.getHealth();
      setHealth(data);
    } catch (err) {
      console.warn('Could not fetch health from backend bridge:', err);
    }
  };

  const refreshManifest = async () => {
    try {
      const data = await systemApi.getManifest();
      if (data && data.success) {
        setManifest(data);
      }
    } catch (err) {
      console.warn('Could not fetch manifest from backend bridge:', err);
    }
  };

  useEffect(() => {
    let mounted = true;

    async function init() {
      setIsLoading(true);
      await Promise.allSettled([
        systemApi.getHealth().then((h) => {
          if (mounted) setHealth(h);
        }),
        systemApi.getManifest().then((m) => {
          if (mounted && m?.success) setManifest(m);
        }),
        systemApi.getSubsystems().then((s) => {
          if (mounted && s?.subsystems?.length > 0) {
            setSubsystems(s.subsystems);
          }
        }),
      ]);
      if (mounted) setIsLoading(false);
    }

    init();

    return () => {
      mounted = false;
    };
  }, []);

  const demoMode = health?.demoMode ?? manifest?.demoMode ?? false;

  return (
    <SystemContext.Provider
      value={{
        health,
        manifest,
        subsystems,
        demoMode,
        isLoading,
        refreshHealth,
        refreshManifest,
      }}
    >
      {children}
    </SystemContext.Provider>
  );
};

export function useSystem() {
  const context = useContext(SystemContext);
  if (!context) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
}
