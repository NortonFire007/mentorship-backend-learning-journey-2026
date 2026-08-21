import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

const meta: Meta<typeof Dialog> = {
  title: "UI/Dialog",
  component: Dialog,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Dialog>;

export const Default: Story = {
  args: {
    isOpen: true,
    title: "Delete Subscription",
    description: "Are you sure you want to delete this alert subscription?",
    onClose: () => {},
    footer: (
      <>
        <Button variant="secondary">Cancel</Button>
        <Button variant="destructive">Confirm Delete</Button>
      </>
    ),
  },
};
