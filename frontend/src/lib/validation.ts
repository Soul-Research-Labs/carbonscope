export interface RegisterFormValues {
  email: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  companyName: string;
  industry: string;
  region: string;
}

export function validateRegisterField(
  field: keyof RegisterFormValues,
  values: RegisterFormValues,
): string {
  const value = values[field];

  switch (field) {
    case "email":
      if (!value) return "Email is required";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return "Enter a valid email address";
      }
      return "";
    case "password":
      if (!value) return "Password is required";
      if (value.length < 8) return "Password must be at least 8 characters";
      if (!/[A-Z]/.test(value) || !/\d/.test(value)) {
        return "Must include an uppercase letter and a digit";
      }
      if (!/[^A-Za-z0-9]/.test(value)) {
        return "Must include a special character";
      }
      return "";
    case "confirmPassword":
      if (!value) return "Confirm your password";
      if (value !== values.password) return "Passwords do not match";
      return "";
    case "fullName":
      return value.trim() ? "" : "Full name is required";
    case "companyName":
      return value.trim() ? "" : "Company name is required";
    case "industry":
      return value.trim() ? "" : "Industry is required";
    case "region":
      return value.trim() ? "" : "Region is required";
    default:
      return "";
  }
}

export function validateRegisterForm(
  values: RegisterFormValues,
): Record<string, string> {
  const fields: Array<keyof RegisterFormValues> = [
    "fullName",
    "companyName",
    "industry",
    "region",
    "email",
    "password",
    "confirmPassword",
  ];

  const errors: Record<string, string> = {};
  for (const field of fields) {
    const message = validateRegisterField(field, values);
    if (message) errors[field] = message;
  }
  return errors;
}

// --- Login validation ---

export interface LoginFormValues {
  email: string;
  password: string;
}

export function validateLoginField(
  field: keyof LoginFormValues,
  values: LoginFormValues,
): string {
  const value = values[field];
  switch (field) {
    case "email":
      if (!value) return "Email is required";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))
        return "Enter a valid email address";
      return "";
    case "password":
      return value ? "" : "Password is required";
    default:
      return "";
  }
}

export function validateLoginForm(
  values: LoginFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of ["email", "password"] as const) {
    const msg = validateLoginField(field, values);
    if (msg) errors[field] = msg;
  }
  return errors;
}

// --- Password change validation ---

export interface PasswordChangeValues {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

export function validatePasswordChangeField(
  field: keyof PasswordChangeValues,
  values: PasswordChangeValues,
): string {
  const value = values[field];
  switch (field) {
    case "currentPassword":
      return value ? "" : "Current password is required";
    case "newPassword":
      if (!value) return "New password is required";
      if (value.length < 8) return "Password must be at least 8 characters";
      if (!/[A-Z]/.test(value) || !/\d/.test(value))
        return "Must include an uppercase letter and a digit";
      if (value === values.currentPassword)
        return "New password must differ from current";
      return "";
    case "confirmNewPassword":
      if (!value) return "Confirm your new password";
      if (value !== values.newPassword) return "Passwords do not match";
      return "";
    default:
      return "";
  }
}

export function validatePasswordChangeForm(
  values: PasswordChangeValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of [
    "currentPassword",
    "newPassword",
    "confirmNewPassword",
  ] as const) {
    const msg = validatePasswordChangeField(field, values);
    if (msg) errors[field] = msg;
  }
  return errors;
}

// --- Profile validation ---

export interface ProfileFormValues {
  fullName: string;
  email: string;
}

export function validateProfileField(
  field: keyof ProfileFormValues,
  values: ProfileFormValues,
): string {
  const value = values[field];
  switch (field) {
    case "fullName":
      return value.trim() ? "" : "Full name is required";
    case "email":
      if (!value) return "Email is required";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))
        return "Enter a valid email address";
      return "";
    default:
      return "";
  }
}

// --- Upload / emission data validation ---

export function validatePositiveNumber(value: string, label: string): string {
  if (!value) return "";
  const n = parseFloat(value);
  if (isNaN(n)) return `${label} must be a number`;
  if (n < 0) return `${label} cannot be negative`;
  return "";
}

export function validateYear(value: number): string {
  if (!Number.isInteger(value)) return "Year must be a whole number";
  if (value < 2000 || value > new Date().getFullYear())
    return `Year must be between 2000 and ${new Date().getFullYear()}`;
  return "";
}
