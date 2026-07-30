import type { Meta, StoryObj } from "@storybook/react";
import { Select } from "./Select";

const meta: Meta<typeof Select> = {
  title: "UI/Select",
  component: Select,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Select>;

export const Default: Story = {
  args: {
    label: "Travel Type",
    options: [
      { value: "flight", label: "Flight" },
      { value: "hotel", label: "Hotel / Apartment" },
      { value: "package", label: "Package Tour" },
    ],
  },
};
