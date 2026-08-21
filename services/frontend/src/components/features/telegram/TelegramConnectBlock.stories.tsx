import type { Meta, StoryObj } from "@storybook/react";
import { TelegramConnectBlock } from "./TelegramConnectBlock";

const meta: Meta<typeof TelegramConnectBlock> = {
  title: "Features/TelegramConnectBlock",
  component: TelegramConnectBlock,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof TelegramConnectBlock>;

export const Default: Story = {};
