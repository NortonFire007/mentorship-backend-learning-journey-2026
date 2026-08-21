import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./Input";

const meta: Meta<typeof Input> = {
  title: "UI/Input",
  component: Input,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = {
  args: {
    label: "Email Address",
    placeholder: "alex@example.com",
  },
};

export const WithError: Story = {
  args: {
    label: "Email Address",
    value: "invalid-email",
    error: "Please enter a valid email address.",
  },
};
