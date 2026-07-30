напиш комит нimport type { Meta, StoryObj } from "@storybook/react";
import { Moon } from "lucide-react";
import { Toggle } from "./Toggle";

const meta: Meta<typeof Toggle> = {
  title: "UI/Toggle",
  component: Toggle,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Toggle>;

export const ThemeToggle: Story = {
  args: {
    label: "Toggle Theme",
    icon: <Moon className="h-5 w-5" />,
  },
};
