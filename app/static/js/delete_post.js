document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded事件触发，开始初始化删除功能');
    
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    console.log('deleteModal元素:', document.getElementById('deleteConfirmModal'));
    console.log('deleteModal实例:', deleteModal);
    
    const deleteBtns = document.querySelectorAll('[data-bs-target="#deleteConfirmModal"]');
    console.log('找到的删除按钮数量:', deleteBtns.length);
    
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    console.log('确认删除按钮元素:', confirmDeleteBtn);
    
    const csrfToken = document.querySelector('meta[name="csrf_token"]').content;
    console.log('CSRF令牌获取状态:', csrfToken ? '成功' : '失败');
    
    let currentForm = null;
    let currentCommentId = null;
    let isDeleting = false; // 添加删除状态标志

    // 为所有删除按钮添加点击事件
    deleteBtns.forEach((btn, index) => {
        console.log(`为删除按钮${index}添加点击事件:`, btn);
        btn.addEventListener('click', function() {
            console.log('删除按钮被点击:', this);
            
            // 检查是否是评论删除按钮
            if (this.classList.contains('delete-comment-btn')) {
                const commentId = this.dataset.commentId;
                console.log(`评论删除 - commentId: ${commentId}`);
                
                // 使用浏览器自带确认框
                if (confirm('确定要删除此评论吗？此操作不可恢复。')) {
                    handleCommentDeleteDirectly(commentId);
                }
            } else {
                // 帖子删除仍使用模态框
                currentForm = this.closest('form');
                currentCommentId = null;
                console.log(`帖子删除 - form:`, currentForm);
                if (currentForm) {
                    document.getElementById('deleteModalTitle').textContent = '确认删除帖子';
                    document.getElementById('deleteModalMessage').textContent = '确定要删除此帖子及其所有评论吗？此操作不可恢复。';
                    deleteModal.show();
                } else {
                    console.log('未找到关联的表单，无法显示模态框');
                }
            }
        });
    });

    // 删除以下代码块
    // 确认删除按钮点击事件
    if (confirmDeleteBtn) {
        console.log('为确认删除按钮添加点击事件');
        // 先移除可能存在的事件监听器，防止重复绑定
        confirmDeleteBtn.removeEventListener('click', handleConfirmDelete);
        confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    } else {
        console.error('未找到确认删除按钮，无法绑定事件');
    }

    // 单独定义确认删除处理函数，便于事件管理
    async function handleConfirmDelete() {
        console.log('确认删除按钮点击事件触发');
        console.log('currentForm:', currentForm);
        console.log('currentCommentId:', currentCommentId);
        
        // 添加并发控制和按钮状态管理
        if (isDeleting) {
            console.log('删除操作已在进行中，请等待完成');
            document.getElementById('deleteModalMessage').textContent = '删除操作已在进行中，请等待完成';
            return;
        }
        
        if (!currentForm && !currentCommentId) {
            console.log('currentForm和currentCommentId都为空，返回');
            return;
        }

        try {
            isDeleting = true;
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.textContent = '删除中...';
            let url, method = 'POST';
            if (currentForm) {
                url = currentForm.action;
            } else if (currentCommentId) {
                url = `/comment/${currentCommentId}/delete`;
            }
            
            console.log('构建的删除URL:', url);
            
            // 添加URL检查
            if (!url) {
                throw new Error('无法确定删除请求URL');
            }

            console.log('发送删除请求到:', url);
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: currentForm ? new URLSearchParams(new FormData(currentForm)) : new URLSearchParams({})
            });

            console.log('删除请求响应状态:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response.status}`);
            }

            // 成功后重定向到论坛页面
            console.log('删除成功，重定向到/forum');
            window.location.href = '/forum';
        } catch (error) {
            console.error('删除请求失败:', error);
            document.getElementById('deleteModalMessage').textContent = `删除失败: ${error.message}`;
            // 保持模态框打开以便用户查看错误
        } finally {
            isDeleting = false;
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.textContent = '确认删除';
            // 仅在成功时关闭模态框，错误时保持打开
            if (!error) {
                deleteModal.hide();
            }
            currentForm = null;
            currentCommentId = null;
        }
    }
});

// 将handleCommentDeleteDirectly函数移至DOMContentLoaded作用域内
async function handleCommentDeleteDirectly(commentId) {
    if (!commentId) {
        console.error('评论ID不存在');
        return;
    }

    try {
        // 直接在函数内部获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf_token"]').content;
        if (!csrfToken) {
            throw new Error('无法获取CSRF令牌，请检查meta标签');
        }

        const url = `/comment/${commentId}/delete`;
        console.log('发送评论删除请求到:', url);

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: new URLSearchParams({})
        });

        console.log('删除请求响应状态:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`);
        }

        console.log('评论删除成功');
        location.reload();
    } catch (error) {
        console.error('删除评论失败:', error);
        alert(`删除失败: ${error.message}`);
    }
}