import type { LocalUser, Scholar } from "../src/types";
export const administrator: LocalUser = {
  id: 1,
  username: "test-admin",
  role: "admin",
  is_active: true,
  must_change_password: false,
};
export const scholar: Scholar = {
  id: 1,
  revision: 1,
  name: "Demonstration Scholar",
  age: 35,
  previous_degree: "Bachelor",
  missing_requirements: false,
  department: "CAS",
  rank: "Instructor I",
  tenure: "5 years",
  participations: [],
  requirements: [],
  personnel_type: "Faculty",
  data_source: "Cathedra",
  created_at: "2026-10-01T00:00:00",
  updated_at: "2026-10-01T00:00:00",
};
