import type { Meta, StoryObj } from "@storybook/react";
import { DateRangePicker } from "./DateRangePicker";

const meta: Meta<typeof DateRangePicker> = {
  title: "UI/DateRangePicker",
  component: DateRangePicker,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof DateRangePicker>;

export const Default: Story = {
  args: {
    label: "Travel Window",
    startDate: "2026-08-01",
    endDate: "2026-08-15",
    onChange: () => {},
  },
};
