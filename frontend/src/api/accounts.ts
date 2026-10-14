import { request } from "./client";
import type { LocalUser, SessionResult } from "../types";

export const getAccountStatus = () => request<{setup_required:boolean}>("/auth/status")
export const setupAdmin = (username:string, password:string, setupToken:string) => request<SessionResult>("/auth/setup", {method:"POST",headers:{"X-Cathedra-Setup":setupToken},body:JSON.stringify({username,password})})
export const signIn = (username:string, password:string) => request<SessionResult>("/auth/login", {method:"POST",body:JSON.stringify({username,password})})
export const signOut = () => request<void>("/auth/logout", {method:"POST"})
export const getUsers = () => request<LocalUser[]>("/auth/users")
export const createUser = (username:string,password:string,role:"admin"|"staff") => request<LocalUser>("/auth/users", {method:"POST",body:JSON.stringify({username,password,role})})
export const changePassword = (current_password:string,new_password:string) => request<void>("/auth/change-password",{method:"POST",body:JSON.stringify({current_password,new_password})})
export const resetUserPassword = (id:number,new_password:string) => request<void>(`/auth/users/${id}/reset-password`,{method:"POST",body:JSON.stringify({new_password})});
export const setUserActive = (id:number,active:boolean) => request<LocalUser>(`/auth/users/${id}/status`,{method:"PUT",body:JSON.stringify({active})});
export const revokeUserSessions = (id:number) => request<void>(`/auth/users/${id}/revoke-sessions`,{method:"POST"});
