import torch
import gradio as gr
import spaces
from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download
from compel import CompelForSDXL

# 1. モデルの初期化
REPO_ID = "IbarakiDouji/Nova-Furry-XL"
FILENAME = "novaFurryXL_ilV180A.safetensors"

print(f"Downloading checkpoint: {FILENAME} ...")
ckpt_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)

print("Loading pipeline to CPU via from_single_file...")
pipe = StableDiffusionXLPipeline.from_single_file(
    ckpt_path,
    torch_dtype=torch.float16,
    use_safetensors=True
)
pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
print("Pipeline loaded successfully!")

# Compel for long prompt support
compel = CompelForSDXL(pipe)
print("Compel initialized for long prompt support!")

# 2. 推論処理
@spaces.GPU(duration=90)
def predict(prompt, negative_prompt, steps, guidance_scale, width, height):
    pipe.to("cuda")

    # Use Compel for long prompt support
    conditioning = compel(prompt, negative_prompt=negative_prompt)

    image = pipe(
        prompt_embeds=conditioning.embeds,
        pooled_prompt_embeds=conditioning.pooled_embeds,
        negative_prompt_embeds=conditioning.negative_embeds,
        negative_pooled_prompt_embeds=conditioning.negative_pooled_embeds,
        num_inference_steps=int(steps),
        guidance_scale=float(guidance_scale),
        width=int(width),
        height=int(height),
    ).images[0]

    return image

# 3. UIおよびAPI定義
demo = gr.Interface(
    fn=predict,
    inputs=[
        gr.Textbox(
            label="Prompt",
            lines=2,
            value="masterpiece, best quality, amazing quality, ultra-detailed, furry, anthro, 1boy, wolf, kemono"
        ),
        gr.Textbox(
            label="Negative Prompt",
            value="worst quality, low quality, bad quality, bad anatomy, bad hands, missing fingers, extra digits, cropped, deformed"
        ),
        gr.Slider(label="Steps", minimum=1, maximum=50, value=25, step=1),
        gr.Slider(label="Guidance Scale", minimum=1, maximum=15, value=5.0, step=0.5),
        gr.Slider(label="Width", minimum=512, maximum=1536, value=1152, step=64),
        gr.Slider(label="Height", minimum=512, maximum=1536, value=768, step=64),
    ],
    outputs=gr.Image(label="Result", type="filepath"),
    api_name="predict"
)

if __name__ == "__main__":
    demo.queue().launch()
