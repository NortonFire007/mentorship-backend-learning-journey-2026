import type { Meta, StoryObj } from "@storybook/react";
import type { SubscriptionRead } from "../../../types/api";
import { SubscriptionCard } from "./SubscriptionCard";

const mockSubscription: SubscriptionRead = {
  id: "sub-123",
  user_id: "user-1",
  destination: "Paris, France",
  travel_type: "hotel",
  provider: "airbnb",
  start_date: "2026-08-01",
  end_date: "2026-08-15",
  adults: 2,
  children: 0,
  flexible_days: 2,
  max_price: 350,
  currency: "USD",
  min_bedrooms: 1,
  min_beds: 1,
  max_stops: null,
  is_active: true,
  last_checked_at: "2026-07-29T10:00:00Z",
  created_at: "2026-07-25T10:00:00Z",
  updated_at: "2026-07-25T10:00:00Z",
};

const meta: Meta<typeof SubscriptionCard> = {
  title: "Features/SubscriptionCard",
  component: SubscriptionCard,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof SubscriptionCard>;

export const Active: Story = {
  args: {
    subscription: mockSubscription,
    onToggleStatus: async () => {},
    onDelete: async () => {},
  },
};

export const Paused: Story = {
  args: {
    subscription: { ...mockSubscription, is_active: false },
    onToggleStatus: async () => {},
    onDelete: async () => {},
  },
};
