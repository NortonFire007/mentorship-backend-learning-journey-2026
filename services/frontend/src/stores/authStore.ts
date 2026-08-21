import { create } from "zustand";
import type { UserRead } from "../types/api";

interface AuthState {
  accessToken: string | null;
  user: UserRead | null;
  setAuth: (token: string, user: UserRead) => void;
  setUser: (user: UserRead) => void;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  user: null,
  setAuth: (accessToken, user) => set({ accessToken, user }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clearAuth: () => set({ accessToken: null, user: null }),
}));
