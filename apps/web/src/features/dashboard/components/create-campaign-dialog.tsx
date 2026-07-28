import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import type { CampaignStatus } from "@/shared/types";

const schema = z.object({
    name: z.string().min(2, "Name your campaign"),
    product: z.string().min(2, "Add a product"),
    status: z.enum(["Live", "Testing", "Paused", "Draft"]),
});
type Values = z.infer<typeof schema>;

export function CreateCampaignDialog({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const addDemoCampaign = useAppStore((s) => s.addDemoCampaign);
    const form = useForm<Values>({
        resolver: zodResolver(schema),
        defaultValues: { name: "", product: "", status: "Draft" as CampaignStatus },
    });

    function onSubmit(v: Values) {
        addDemoCampaign({
            id: `c-${Date.now()}`,
            name: v.name,
            product: v.product,
            status: v.status,
            activeAssets: 0,
            ugcScore: 0,
            gmv: 0,
            nextAction: "Add creative references",
        });
        onOpenChange(false);
        form.reset();
        toast.success("Campaign created", { description: `“${v.name}” saved as ${v.status}.` });
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[480px]">
                <DialogHeader>
                    <DialogTitle>Create campaign</DialogTitle>
                    <DialogDescription>
                        Set up a new campaign shell. You can attach creative references and creators
                        later.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
                    <div className="grid gap-1.5">
                        <Label htmlFor="cname">Campaign name</Label>
                        <Input
                            id="cname"
                            placeholder="e.g. Kitchen Organizer US Launch"
                            {...form.register("name")}
                        />
                        {form.formState.errors.name && (
                            <p className="text-xs text-destructive">
                                {form.formState.errors.name.message}
                            </p>
                        )}
                    </div>
                    <div className="grid gap-1.5">
                        <Label htmlFor="cprod">Product</Label>
                        <Input
                            id="cprod"
                            placeholder="e.g. Under-sink Sliding Organizer"
                            {...form.register("product")}
                        />
                        {form.formState.errors.product && (
                            <p className="text-xs text-destructive">
                                {form.formState.errors.product.message}
                            </p>
                        )}
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Status</Label>
                        <Controller
                            control={form.control}
                            name="status"
                            render={({ field }) => (
                                <Select value={field.value} onValueChange={field.onChange}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Draft">Draft</SelectItem>
                                        <SelectItem value="Testing">Testing</SelectItem>
                                        <SelectItem value="Live">Live</SelectItem>
                                        <SelectItem value="Paused">Paused</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}
                        />
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit">Create campaign</Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
