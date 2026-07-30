import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "UI/Badge",
  component: Badge,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Success: Story = {
  args: {
    children: "SENT",
    variant: "success",
  },
};

export const Warning: Story = {
  args: {
    children: "PENDING",
    variant: "warning",
  },
};

export const ErrorBadge: Story = {
  args: {
    children: "FAILED",
    variant: "error",
  },
};

export const Muted: Story = {
  args: {
    children: "SKIPPED",
    variant: "muted",
  },
};
