import torch
import gradio as gr
import spaces
from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download

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


def get_prompt_hidden_states_sdxl(prompt_embeds, clip_skip=None):
    """Get penultimate layer hidden states for SDXL."""
    if clip_skip is None:
        return prompt_embeds.hidden_states[-2]
    return prompt_embeds.hidden_states[-(clip_skip + 2)]


def tokenize_long_prompt(tokenizer, prompt):
    """Tokenize prompt without truncation, returning token ids."""
    if not prompt:
        prompt = "empty"
    tokens = tokenizer(prompt, truncation=False).input_ids[1:-1]
    return list(tokens)


def group_into_chunks(tokens, eos_token_id, bos_token_id=49406):
    """Group tokens into 75-token chunks with BOS/EOS."""
    chunks = []
    while len(tokens) >= 75:
        head_75 = [tokens.pop(0) for _ in range(75)]
        chunk = [bos_token_id] + head_75 + [eos_token_id]
        chunks.append(chunk)
    if tokens:
        chunk = [bos_token_id] + tokens + [eos_token_id] * (75 - len(tokens)) + [eos_token_id]
        chunks.append(chunk)
    if not chunks:
        chunk = [bos_token_id] + [eos_token_id] * 75 + [eos_token_id]
        chunks.append(chunk)
    return chunks


def get_long_prompt_embeddings_sdxl(pipe, prompt, neg_prompt):
    """
    Generate long prompt embeddings for SDXL based on sd_embed implementation.
    Returns: prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds
    """
    device = pipe.device

    # Tokenize both prompts with both tokenizers
    prompt_tokens_1 = tokenize_long_prompt(pipe.tokenizer, prompt)
    neg_prompt_tokens_1 = tokenize_long_prompt(pipe.tokenizer, neg_prompt)

    prompt_tokens_2 = tokenize_long_prompt(pipe.tokenizer_2, prompt)
    neg_prompt_tokens_2 = tokenize_long_prompt(pipe.tokenizer_2, neg_prompt)

    # Pad positive and negative to same length for tokenizer 1
    eos_1 = pipe.tokenizer.eos_token_id
    prompt_len_1 = len(prompt_tokens_1)
    neg_prompt_len_1 = len(neg_prompt_tokens_1)
    if prompt_len_1 > neg_prompt_len_1:
        neg_prompt_tokens_1 += [eos_1] * (prompt_len_1 - neg_prompt_len_1)
    else:
        prompt_tokens_1 += [eos_1] * (neg_prompt_len_1 - prompt_len_1)

    # Pad positive and negative to same length for tokenizer 2
    eos_2 = pipe.tokenizer_2.eos_token_id
    prompt_len_2 = len(prompt_tokens_2)
    neg_prompt_len_2 = len(neg_prompt_tokens_2)
    if prompt_len_2 > neg_prompt_len_2:
        neg_prompt_tokens_2 += [eos_2] * (prompt_len_2 - neg_prompt_len_2)
    else:
        prompt_tokens_2 += [eos_2] * (neg_prompt_len_2 - prompt_len_2)

    # Group into chunks
    prompt_chunks_1 = group_into_chunks(prompt_tokens_1.copy(), eos_1)
    neg_prompt_chunks_1 = group_into_chunks(neg_prompt_tokens_1.copy(), eos_1)
    prompt_chunks_2 = group_into_chunks(prompt_tokens_2.copy(), eos_2)
    neg_prompt_chunks_2 = group_into_chunks(neg_prompt_tokens_2.copy(), eos_2)

    # Ensure same number of chunks across all 4 lists
    max_chunks = max(
        len(prompt_chunks_1),
        len(prompt_chunks_2),
        len(neg_prompt_chunks_1),
        len(neg_prompt_chunks_2),
    )
    while len(prompt_chunks_1) < max_chunks:
        prompt_chunks_1.append([49406] + [eos_1] * 75 + [eos_1])
        prompt_chunks_2.append([49406] + [eos_2] * 75 + [eos_2])
    while len(neg_prompt_chunks_1) < max_chunks:
        neg_prompt_chunks_1.append([49406] + [eos_1] * 75 + [eos_1])
        neg_prompt_chunks_2.append([49406] + [eos_2] * 75 + [eos_2])

    embeds = []
    neg_embeds = []
    pooled_prompt_embeds = None
    negative_pooled_prompt_embeds = None

    with torch.no_grad():
        for i in range(max_chunks):
            # Positive prompt
            token_tensor_1 = torch.tensor([prompt_chunks_1[i]], dtype=torch.long, device=device)
            token_tensor_2 = torch.tensor([prompt_chunks_2[i]], dtype=torch.long, device=device)

            prompt_embeds_1 = pipe.text_encoder(token_tensor_1, output_hidden_states=True)
            prompt_hidden_1 = get_prompt_hidden_states_sdxl(prompt_embeds_1)

            prompt_embeds_2 = pipe.text_encoder_2(token_tensor_2, output_hidden_states=True)
            prompt_hidden_2 = get_prompt_hidden_states_sdxl(prompt_embeds_2)
            if pooled_prompt_embeds is None:
                pooled_prompt_embeds = prompt_embeds_2[0]

            token_embedding = torch.cat([prompt_hidden_1, prompt_hidden_2], dim=-1)
            embeds.append(token_embedding)

            # Negative prompt
            neg_token_tensor_1 = torch.tensor([neg_prompt_chunks_1[i]], dtype=torch.long, device=device)
            neg_token_tensor_2 = torch.tensor([neg_prompt_chunks_2[i]], dtype=torch.long, device=device)

            neg_prompt_embeds_1 = pipe.text_encoder(neg_token_tensor_1, output_hidden_states=True)
            neg_prompt_hidden_1 = get_prompt_hidden_states_sdxl(neg_prompt_embeds_1)

            neg_prompt_embeds_2 = pipe.text_encoder_2(neg_token_tensor_2, output_hidden_states=True)
            neg_prompt_hidden_2 = get_prompt_hidden_states_sdxl(neg_prompt_embeds_2)
            if negative_pooled_prompt_embeds is None:
                negative_pooled_prompt_embeds = neg_prompt_embeds_2[0]

            neg_token_embedding = torch.cat([neg_prompt_hidden_1, neg_prompt_hidden_2], dim=-1)
            neg_embeds.append(neg_token_embedding)

    # Concatenate chunks along sequence dimension (dim=1)
    prompt_embeds = torch.cat(embeds, dim=1)
    negative_prompt_embeds = torch.cat(neg_embeds, dim=1)

    # Ensure dtype matches text_encoder_2
    prompt_embeds = prompt_embeds.to(dtype=pipe.text_encoder_2.dtype, device=device)

    return prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds


# 2. 推論処理
@spaces.GPU(duration=90)
def predict(prompt, negative_prompt, steps, guidance_scale, width, height):
    pipe.to("cuda")

    # Generate embeddings with long prompt support
    prompt_embeds, neg_prompt_embeds, pooled_embeds, neg_pooled_embeds = \
        get_long_prompt_embeddings_sdxl(pipe, prompt, negative_prompt)

    image = pipe(
        prompt_embeds=prompt_embeds,
        pooled_prompt_embeds=pooled_embeds,
        negative_prompt_embeds=neg_prompt_embeds,
        negative_pooled_prompt_embeds=neg_pooled_embeds,
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
