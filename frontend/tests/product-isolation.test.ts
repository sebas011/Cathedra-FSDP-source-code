import { expect, it } from "vitest";
import { product, productName } from "../src/product";
import { API, getCurrentUser, saveSession, clearSession } from "../src/api/client";
import { administrator } from "./fixtures";

it("FSDP uses only its own service and session storage", () => {
  localStorage.setItem("cathedra-faculty-session", JSON.stringify({ token: "other-app" }));
  expect(product).toBe("fsdp");
  expect(productName).toBe("Cathedra FSDP");
  expect(API).toContain("8101");
  expect(getCurrentUser()).toBeNull();
  saveSession({ token: "synthetic-fsdp", user: administrator });
  expect(sessionStorage.getItem("cathedra-fsdp-session")).toContain("synthetic-fsdp");
  expect(localStorage.getItem("cathedra-fsdp-session")).toBeNull();
  clearSession();
  expect(localStorage.getItem("cathedra-faculty-session")).toContain("other-app");
});
