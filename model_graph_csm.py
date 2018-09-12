# -*- coding: utf-8 -*-
"""
Created on Sun Aug 26 07:40:52 2018

@author: limingfan

"""

import tensorflow as tf

from zoo_layers import att_pool_layer, dot_att_layer
from zoo_layers import gather_and_pad_layer


def build_graph(config):
    
    input_x = tf.placeholder(tf.int32, [None, None], name='input_x')
    input_n = tf.placeholder(tf.int32, [None], name='input_n')
    input_y = tf.placeholder(tf.int64, [None], name='input_y')

    with tf.device('/cpu:0'):
        emb_mat = tf.get_variable('embedding',
                                  [config.vocab.size(), config.vocab.emb_dim],
                                  initializer=tf.constant_initializer(config.vocab.embeddings),
                                  trainable = config.emb_tune)
        seq_emb = tf.nn.embedding_lookup(emb_mat, input_x)
        
        # seq_mask = tf.cast(tf.cast(input_x, dtype = tf.bool), dtype = tf.int32)
        # seq_len = tf.reduce_sum(seq_mask, 1)

    with tf.name_scope("csm"):
        
        conv1_5 = tf.layers.conv1d(seq_emb, 128, 5, padding='same', name='conv1_5')
        conv1_3 = tf.layers.conv1d(seq_emb, 128, 3, padding='same', name='conv1_3')
        conv1_2 = tf.layers.conv1d(seq_emb, 128, 2, padding='same', name='conv1_2')
        
        feat1 = tf.reduce_max(conv1_5, reduction_indices=[1], name='feat1')
        feat2 = tf.reduce_max(conv1_3, reduction_indices=[1], name='feat2')
        feat3 = tf.reduce_max(conv1_2, reduction_indices=[1], name='feat3')
        
        feat_s = tf.concat([feat1, feat2, feat3], 1)
        
        #
        feat_g, mask_s = gather_and_pad_layer(feat_s, input_n)  # (B, S, D)
        
        #
        B = tf.shape(feat_g)[0]
        num_heads = 2
        att_dim = 128
        
        feat = []
        for idx in range(num_heads):
            trans = dot_att_layer(feat_g, feat_g, mask_s, 256, 
                                  keep_prob = config.keep_prob, gating = False,
                                  scope = "dot_attention_" + str(idx))
            
            query = tf.get_variable("query_" + str(idx), [att_dim],
                                    initializer = tf.ones_initializer())
            query = tf.tile(tf.expand_dims(query, 0), [B, 1])     
            
            feat_c = att_pool_layer(trans, query, mask_s, att_dim,
                                    config.keep_prob, is_train = None,
                                    scope = "att_pooling_" + str(idx))
            feat.append(feat_c)
        #            
        feat = tf.concat(feat, 1)
        #

    with tf.name_scope("score"):
        #
        fc = tf.nn.dropout(feat, config.keep_prob)
        fc = tf.layers.dense(fc, 128, name='fc1')            
        fc = tf.nn.relu(fc)
        
        fc = tf.nn.dropout(fc, config.keep_prob)
        logits = tf.layers.dense(fc, config.num_classes, name='fc2')
        # logits = tf.nn.sigmoid(logits)
        
        normed_logits = tf.nn.softmax(logits, name='logits')          
        y_pred_cls = tf.argmax(logits, 1, name='pred_cls')
        
    with tf.name_scope("loss"):
        #
        cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits = logits,
                                                                       labels = input_y)
        loss = tf.reduce_mean(cross_entropy, name = 'loss')

    with tf.name_scope("accuracy"):
        #
        correct_pred = tf.equal(input_y, y_pred_cls)
        acc = tf.reduce_mean(tf.cast(correct_pred, tf.float32), name = 'metric')
    
    #
    print(normed_logits)
    print(acc)
    print(loss)
    print()
    #

