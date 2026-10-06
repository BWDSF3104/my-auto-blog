import torch
import gradio as gr
import spaces
from diffusers import StableDiffusionXLPipeline, EulerAncestralDiscreteScheduler
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
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)

# negative prompt は全リクエストで同一のため、embeddingをキャッシュ
_cached_neg_prompt = "nsfw, worst quality, bad anatomy, deformed, bad hands, missing fingers, extra digits, fewer digits, cropped, very displeasing, ugly, jpeg artifacts, signature, watermark, username"
_cached_neg_embeds = None

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


def _tokenize_and_chunk(tokens, eos_token_id):
    """Token list を 75トークン単位でチャンク分割"""
    chunks = []
    while len(tokens) >= 75:
        head_75 = [tokens.pop(0) for _ in range(75)]
        chunk = [49406] + head_75 + [eos_token_id]
        chunks.append(chunk)
    if tokens:
        chunk = [49406] + tokens + [eos_token_id] * (75 - len(tokens)) + [eos_token_id]
        chunks.append(chunk)
    if not chunks:
        chunk = [49406] + [eos_token_id] * 75 + [eos_token_id]
        chunks.append(chunk)
    return chunks


def _encode_chunks(pipe, chunks, device):
    """チャンクリストをtext encoderに通してembeddingを返す"""
    embeds = []
    pooled = None
    with torch.no_grad():
        for chunk in chunks:
            token_tensor = torch.tensor([chunk], dtype=torch.long, device=device)
            out1 = pipe.text_encoder(token_tensor, output_hidden_states=True)
            hidden1 = get_prompt_hidden_states_sdxl(out1)
            out2 = pipe.text_encoder_2(token_tensor, output_hidden_states=True)
            hidden2 = get_prompt_hidden_states_sdxl(out2)
            if pooled is None:
                pooled = out2[0]
            embeds.append(torch.cat([hidden1, hidden2], dim=-1))
    return torch.cat(embeds, dim=1), pooled


def get_long_prompt_embeddings_sdxl(pipe, prompt, neg_prompt):
    """
    Generate long prompt embeddings for SDXL based on sd_embed implementation.
    negative prompt は同一内容の場合にキャッシュを返す。
    Returns: prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds
    """
    global _cached_neg_embeds
    device = pipe.device

    # Tokenize (BOS/EOS除去)
    prompt_tokens_1 = tokenize_long_prompt(pipe.tokenizer, prompt)
    prompt_tokens_2 = tokenize_long_prompt(pipe.tokenizer_2, prompt)

    # Pad tokenizer 1
    eos_1 = pipe.tokenizer.eos_token_id
    neg_tokens_1 = tokenize_long_prompt(pipe.tokenizer, neg_prompt)
    if len(prompt_tokens_1) > len(neg_tokens_1):
        neg_tokens_1 += [eos_1] * (len(prompt_tokens_1) - len(neg_tokens_1))
    else:
        prompt_tokens_1 += [eos_1] * (len(neg_tokens_1) - len(prompt_tokens_1))

    # Pad tokenizer 2
    eos_2 = pipe.tokenizer_2.eos_token_id
    neg_tokens_2 = tokenize_long_prompt(pipe.tokenizer_2, neg_prompt)
    if len(prompt_tokens_2) > len(neg_tokens_2):
        neg_tokens_2 += [eos_2] * (len(prompt_tokens_2) - len(neg_tokens_2))
    else:
        prompt_tokens_2 += [eos_2] * (len(neg_tokens_2) - len(prompt_tokens_2))

    # Chunk分割
    prompt_chunks_1 = _tokenize_and_chunk(prompt_tokens_1.copy(), eos_1)
    prompt_chunks_2 = _tokenize_and_chunk(prompt_tokens_2.copy(), eos_2)
    neg_chunks_1 = _tokenize_and_chunk(neg_tokens_1.copy(), eos_1)
    neg_chunks_2 = _tokenize_and_chunk(neg_tokens_2.copy(), eos_2)

    # チャンク数合わせ
    max_chunks = max(len(prompt_chunks_1), len(prompt_chunks_2), len(neg_chunks_1), len(neg_chunks_2))
    empty_1 = [49406] + [eos_1] * 75 + [eos_1]
    empty_2 = [49406] + [eos_2] * 75 + [eos_2]
    while len(prompt_chunks_1) < max_chunks:
        prompt_chunks_1.append(empty_1[:])
        prompt_chunks_2.append(empty_2[:])
    while len(neg_chunks_1) < max_chunks:
        neg_chunks_1.append(empty_1[:])
        neg_chunks_2.append(empty_2[:])

    # Positive prompt のembedding (常に再計算)
    pos_embeds_1 = []
    pos_embeds_2 = []
    pooled_prompt_embeds = None
    with torch.no_grad():
        for i in range(max_chunks):
            t1 = torch.tensor([prompt_chunks_1[i]], dtype=torch.long, device=device)
            t2 = torch.tensor([prompt_chunks_2[i]], dtype=torch.long, device=device)
            o1 = pipe.text_encoder(t1, output_hidden_states=True)
            o2 = pipe.text_encoder_2(t2, output_hidden_states=True)
            pos_embeds_1.append(get_prompt_hidden_states_sdxl(o1))
            pos_embeds_2.append(get_prompt_hidden_states_sdxl(o2))
            if pooled_prompt_embeds is None:
                pooled_prompt_embeds = o2[0]

    prompt_embeds = torch.cat([torch.cat([e1, e2], dim=-1)
                               for e1, e2 in zip(pos_embeds_1, pos_embeds_2)], dim=1)
    prompt_embeds = prompt_embeds.to(dtype=pipe.text_encoder_2.dtype, device=device)

    # Negative prompt のembedding (キャッシュ使用)
    neg_key = (max_chunks, tuple(tuple(c) for c in neg_chunks_1), tuple(tuple(c) for c in neg_chunks_2))
    if _cached_neg_embeds and _cached_neg_embeds['key'] == neg_key and _cached_neg_embeds['device'] == device:
        negative_prompt_embeds = _cached_neg_embeds['embeds'].to(device=device)
        negative_pooled_prompt_embeds = _cached_neg_embeds['pooled'].to(device=device)
    else:
        neg_embeds_1 = []
        neg_embeds_2 = []
        negative_pooled_prompt_embeds = None
        with torch.no_grad():
            for i in range(max_chunks):
                t1 = torch.tensor([neg_chunks_1[i]], dtype=torch.long, device=device)
                t2 = torch.tensor([neg_chunks_2[i]], dtype=torch.long, device=device)
                o1 = pipe.text_encoder(t1, output_hidden_states=True)
                o2 = pipe.text_encoder_2(t2, output_hidden_states=True)
                neg_embeds_1.append(get_prompt_hidden_states_sdxl(o1))
                neg_embeds_2.append(get_prompt_hidden_states_sdxl(o2))
                if negative_pooled_prompt_embeds is None:
                    negative_pooled_prompt_embeds = o2[0]

        negative_prompt_embeds = torch.cat([torch.cat([e1, e2], dim=-1)
                                            for e1, e2 in zip(neg_embeds_1, neg_embeds_2)], dim=1)
        _cached_neg_embeds = {
            'key': neg_key,
            'device': device,
            'embeds': negative_prompt_embeds.to("cpu"),
            'pooled': negative_pooled_prompt_embeds.to("cpu"),
        }

    return prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds


# 2. 推論処理
@spaces.GPU(duration=20)
def predict(prompt, negative_prompt, steps, guidance_scale, width, height, seed=-1):
    # ZeroGPUセッション中はモデルがメモリに残るので、GPU移動は1回だけ
    if pipe.device != torch.device("cuda"):
        pipe.to("cuda")

    # seed が指定された場合は再現性のためにgeneratorを設定
    generator = None
    if seed >= 0:
        generator = torch.Generator(device="cuda").manual_seed(seed)

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
        generator=generator,
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
        gr.Number(label="Seed", value=-1, precision=0,
                  info="-1 for random, >=0 for reproducible results"),
    ],
    outputs=gr.Image(label="Result", type="filepath"),
    api_name="predict"
)

if __name__ == "__main__":
    demo.queue().launch()
