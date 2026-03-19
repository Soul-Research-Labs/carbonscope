import { describe, it, expect } from "vitest";
import {
  validateRegisterField,
  validateRegisterForm,
  type RegisterFormValues,
} from "@/lib/validation";

function makeValid(): RegisterFormValues {
  return {
    email: "valid@example.com",
    password: "Secure123",
    confirmPassword: "Secure123",
    fullName: "Valid User",
    companyName: "Valid Corp",
    industry: "technology",
    region: "US",
  };
}

describe("register validation", () => {
  it("accepts a valid form", () => {
    const values = makeValid();
    expect(validateRegisterForm(values)).toEqual({});
  });

  it("rejects invalid email format", () => {
    const values = makeValid();
    values.email = "not-an-email";
    expect(validateRegisterField("email", values)).toContain("valid email");
  });

  it("rejects weak password", () => {
    const values = makeValid();
    values.password = "short";
    values.confirmPassword = "short";
    expect(validateRegisterField("password", values)).toContain("at least 8");
  });

  it("rejects mismatched confirm password", () => {
    const values = makeValid();
    values.confirmPassword = "Mismatch123";
    expect(validateRegisterField("confirmPassword", values)).toContain(
      "do not match",
    );
  });

  it("returns 'Email is required' for empty email", () => {
    const values = makeValid();
    values.email = "";
    expect(validateRegisterField("email", values)).toBe("Email is required");
  });

  it("returns 'Password is required' for empty password", () => {
    const values = makeValid();
    values.password = "";
    expect(validateRegisterField("password", values)).toBe(
      "Password is required",
    );
  });

  it("rejects password without uppercase letter", () => {
    const values = makeValid();
    values.password = "alllower1";
    values.confirmPassword = "alllower1";
    expect(validateRegisterField("password", values)).toContain(
      "uppercase letter",
    );
  });

  it("rejects password without digit", () => {
    const values = makeValid();
    values.password = "Allupper";
    values.confirmPassword = "Allupper";
    expect(validateRegisterField("password", values)).toContain(
      "uppercase letter and a digit",
    );
  });

  it("returns 'Confirm your password' for empty confirmPassword", () => {
    const values = makeValid();
    values.confirmPassword = "";
    expect(validateRegisterField("confirmPassword", values)).toBe(
      "Confirm your password",
    );
  });

  it("returns error for each empty required field", () => {
    const values = makeValid();
    values.fullName = "";
    expect(validateRegisterField("fullName", values)).toBe(
      "Full name is required",
    );
    values.companyName = "";
    expect(validateRegisterField("companyName", values)).toBe(
      "Company name is required",
    );
    values.industry = "";
    expect(validateRegisterField("industry", values)).toBe(
      "Industry is required",
    );
    values.region = "";
    expect(validateRegisterField("region", values)).toBe(
      "Region is required",
    );
  });

  it("validateRegisterForm returns all errors for fully empty form", () => {
    const empty: RegisterFormValues = {
      email: "",
      password: "",
      confirmPassword: "",
      fullName: "",
      companyName: "",
      industry: "",
      region: "",
    };
    const errors = validateRegisterForm(empty);
    expect(Object.keys(errors)).toHaveLength(7);
    expect(errors.email).toBeTruthy();
    expect(errors.password).toBeTruthy();
    expect(errors.confirmPassword).toBeTruthy();
    expect(errors.fullName).toBeTruthy();
    expect(errors.companyName).toBeTruthy();
    expect(errors.industry).toBeTruthy();
    expect(errors.region).toBeTruthy();
  });
});
