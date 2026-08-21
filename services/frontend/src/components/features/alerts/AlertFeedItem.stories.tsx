import type { Meta, StoryObj } from "@storybook/react";
import type { AlertRead } from "../../../types/api";
import { AlertFeedItem } from "./AlertFeedItem";

const mockAlert: AlertRead = {
  id: "alert-1",
  subscription_id: "sub-123",
  price_found: 280,
  status: "SENT",
  image_url: null,
  deep_link: "https://airbnb.com/rooms/12345",
  error_reason: null,
  created_at: "2026-07-29T14:30:00Z",
};

const meta: Meta<typeof AlertFeedItem> = {
  title: "Features/AlertFeedItem",
  component: AlertFeedItem,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof AlertFeedItem>;

export const Sent: Story = {
  args: {
    alert: mockAlert,
  },
};

export const Failed: Story = {
  args: {
    alert: {
      ...mockAlert,
      status: "FAILED",
      deep_link: null,
      error_reason: "Scraper timeout",
    },
  },
};
