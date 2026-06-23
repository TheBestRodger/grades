export interface DemoUser {
  id: number;
  full_name: string;
  email: string;
  username: string | null;
  role: "hr" | "manager" | "employee";
  is_hr: boolean;
  is_demo: boolean;
}

export interface AuthUser extends DemoUser {}

export interface MagicLinkResponse {
  email: string;
  delivery_mode: "local_link" | "email";
  expires_at: string;
  login_token: string | null;
  login_url: string | null;
  message: string;
}

export interface AuthSession {
  token: string;
  expires_at: string;
  user: AuthUser;
}
