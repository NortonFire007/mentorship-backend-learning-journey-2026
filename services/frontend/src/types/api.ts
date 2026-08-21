export type TravelType = "flight" | "hotel" | "package";
export type Currency = "USD" | "EUR" | "UAH";
export type AlertStatus = "SENT" | "SKIPPED" | "FAILED" | "PENDING";

export interface UserRead {
  id: string;
  email: string;
  name: string;
  surname: string;
  is_active: boolean;
  is_superuser: boolean;
  preferred_currency: Currency;
  telegram_chat_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserWithSubscriptionsRead extends UserRead {
  subscriptions: SubscriptionRead[];
}

export interface SubscriptionRead {
  id: string;
  user_id: string;
  destination: string;
  travel_type: TravelType;
  provider: string;
  start_date: string | null;
  end_date: string | null;
  adults: number;
  children: number;
  flexible_days: number | null;
  max_price: number;
  currency: Currency;
  min_bedrooms: number | null;
  min_beds: number | null;
  max_stops: number | null;
  is_active: boolean;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreate {
  destination: string;
  travel_type: TravelType;
  provider?: string;
  start_date?: string | null;
  end_date?: string | null;
  adults?: number;
  children?: number;
  flexible_days?: number | null;
  max_price: number;
  currency?: Currency;
  min_bedrooms?: number | null;
  min_beds?: number | null;
  max_stops?: number | null;
}

export interface SubscriptionUpdate {
  destination?: string;
  travel_type?: TravelType;
  start_date?: string | null;
  end_date?: string | null;
  adults?: number;
  children?: number;
  flexible_days?: number | null;
  max_price?: number;
  currency?: Currency;
  min_bedrooms?: number | null;
  min_beds?: number | null;
  max_stops?: number | null;
  is_active?: boolean;
}

export interface AlertRead {
  id: string;
  subscription_id: string;
  price_found: number;
  status: AlertStatus;
  image_url: string | null;
  deep_link: string | null;
  error_reason: string | null;
  created_at: string;
}

export interface TelegramLinkResponse {
  link: string;
  expires_in_seconds: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorResponse {
  detail: string | ApiErrorDetail[];
}
